from fastapi.testclient import TestClient
from main import app
from auth import get_db
from database import Base
from test_database import TestingSessionLocal, test_engine
import pytest

@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)    

def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == 200


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "running"

def test_register():
    response = client.post("/register", json={"username": "testuser123", "password": "testpassword123"})
    assert response.status_code == 200
    assert response.json()["message"] == "User registered successfully"

def test_login():
    client.post("/register", json={"username": "testuser123", "password": "testpassword123"})
    response = client.post("/login", data={"username": "testuser123", "password": "testpassword123"})
    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_predict_authenticated():
    client.post("/register", json={"username": "testuser123", "password": "testpassword123"})
    login_response = client.post("/login", data={"username": "testuser123", "password": "testpassword123"})
    token = login_response.json()["access_token"]

    response = client.post("/predict",
        json={
            "MedInc": 5.0,
            "HouseAge": 20,
            "AveRooms": 3.0,
            "AveBedrms": 2.0,
            "Population": 1000,
            "AveOccup": 2.0,
            "Latitude": 37.0,
            "Longitude": -122.0
        },
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert "prediction" in response.json()


def test_predict_without_token():
    response = client.post("/predict",
        json={
            "MedInc": 5.0,
            "HouseAge": 20,
            "AveRooms": 3.0,
            "AveBedrms": 2.0,
            "Population": 1000,
            "AveOccup": 2.0,
            "Latitude": 37.0,
            "Longitude": -122.0
        }
    )

    assert response.status_code == 401

def test_predict_invalid_token():
    response = client.post("/predict",
        json={
            "MedInc": 5.0,
            "HouseAge": 20,
            "AveRooms": 3.0,
            "AveBedrms": 2.0,
            "Population": 1000,
            "AveOccup": 2.0,
            "Latitude": 37.0,
            "Longitude": -122.0
        },
        headers={"Authorization": "Bearer invalid token"}
    )

    assert response.status_code == 401


def test_login_wrong_password():
    client.post("/register", json={"username": "testuser123", "password": "testpassword123"})
    response = client.post("/login", data={"username": "testuser123", "password": "wrongpassword"})
    assert response.status_code == 401


def test_predict_file():
    client.post("/register", json={"username": "testuser123", "password": "testpassword123"})
    login_response = client.post("/login", data={"username": "testuser123", "password": "testpassword123"})    
    token = login_response.json()["access_token"]

    csv_content = """MedInc,HouseAge,AveRooms,AveBedrms,Population,AveOccup,Latitude,Longitude\n5.0,20,3.0,2.0,1000,2.0,37.0,-122.0"""

    print(csv_content)
    response = client.post("/predict-file",
        files={"file": ("test.csv", csv_content, "text/csv")},
        headers={"Authorization": f"Bearer {token}"}       
    )

    assert response.status_code == 200,response.json()
    assert "predicted_price" in response.text


def test_predict_file_invalid_format():
    client.post("/register", json={"username": "testuser123", "password": "testpassword123"})
    login_response = client.post("/login", data={"username": "testuser123", "password": "testpassword123"})    
    token = login_response.json()["access_token"]

    response = client.post("/predict-file",
        files={"file": ("test.txt", "some text", "text/plain")},
        headers={"Authorization": f"Bearer {token}"}       
    )

    assert response.status_code == 400


def test_predict_file_missing_columns():
    client.post("/register", json={"username": "testuser123", "password": "testpassword123"})
    login_response = client.post("/login", data={"username": "testuser123", "password": "testpassword123"})
    token = login_response.json()["access_token"]

    csv_content = """HouseAge,AveRooms,AveBedrms,Population,AveOccup,Latitude\n20,3.0,2.0,1000,2.0,37.0"""

    response = client.post("/predict-file",
        files={"file": ("test.csv", csv_content, "text/csv")},
        headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 400
    assert "Missing required columns" in response.json()["detail"]


def test_predict_file_empty():
    client.post("/register", json={"username": "testuser123", "password": "testpassword123"})
    login_response = client.post("/login", data={"username": "testuser123", "password": "testpassword123"})
    token = login_response.json()["access_token"]

    csv_content = """MedInc,HouseAge,AveRooms,AveBedrms,Population,AveOccup,Latitude,Longitude"""

    response = client.post("/predict-file",
        files={"file": ("empty.csv", csv_content, "text/csv")},
        headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 400
    assert "The uploaded CSV file is empty." in response.json()["detail"]