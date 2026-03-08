from fastapi import APIRouter
from models.doymos_reader import bike_reader

router = APIRouter(prefix="/workout", tags=["workout"])



@router.get("/current")
def get_current():
    return bike_reader.state



