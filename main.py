import joblib
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
import io
import models
from fastapi.security import OAuth2PasswordRequestForm
# from database import Base, engine

from schemas import HouseFeatures, UserCreate

from auth import (get_db, get_password_hash, verify_password, create_access_token, get_current_user,
oauth2_scheme)
    

app = FastAPI()

# Base.metadata.create_all(bind=engine)

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = get_password_hash(user.password)
    new_user = models.User(username=user.username, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully"}


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}



model = joblib.load("house_model.joblib")
feature_names = model.feature_names_in_


@app.get("/")
def home():
    return {"message": "Welcome to the House Price Prediction API",
            "status": 200,
            "description": "This API predicts house prices based on various features."}

@app.get("/health")
def health():
    return {
        "status": "running",
        "model": "random_forest_regressor",
        "features": list(feature_names),
        "avg_error": "$39,000"
    }

@app.post("/predict")
def predict(house: HouseFeatures, current_user= Depends(get_current_user)):
    try:
        features = pd.DataFrame(house.model_dump(), index=[0])
        prediction = model.predict(features)[0]
        price_usd = prediction * 100000  # Assuming the model predicts in units of $100,000
        return {"prediction": f"${price_usd:.2f}",
                "predicted_price_short": f"${prediction:.2f} hundred thousands",
                "confidence_range": f"${price_usd - 39000:.0f} - ${price_usd + 39000:.0f}",
                "api_info": {
                    "username": current_user.username,
                    "id": current_user.id
                },
                "status": 200}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"prediction failed: {str(e)}")


@app.post("/predict-file")
async def predict_file(file: UploadFile = File(...), current_user = Depends(get_current_user)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV file.")

    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents))
    print(df.columns.tolist())
    required_columns = set(feature_names)
    # print(df.dtypes)

    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing_columns)}")

    if len(df) == 0:
        raise HTTPException(status_code=400, detail="The uploaded CSV file is empty.")

    try:
        predictions = model.predict(df)
        df["predicted_price"] = [f"${x:.0f}" for x in predictions]
        output = df.to_csv(index=False)  

        return StreamingResponse(io.StringIO(output), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=predictions.csv"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")



    

