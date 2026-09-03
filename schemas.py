from pydantic import BaseModel, Field

class HouseFeatures(BaseModel):
    MedInc: float = Field(gt=0, description="Median income in neighborhood")
    HouseAge: int = Field(gt=0, description="Average age of houses in neighborhood")
    AveRooms: float = Field(gt=0, description="Average number of rooms per house")
    AveBedrms: float = Field(gt=0, description="Average number of bedrooms per house")
    Population: int = Field(gt=0, description="Total number of people in the neighborhood")
    AveOccup: float = Field(gt=0, description="Average number of occupants per house")
    Latitude: float = Field(gt=-90, lt=90, description="Latitude of the location")
    Longitude: float = Field(gt=-180, lt=180, description="Longitude of the location")
    

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=72)