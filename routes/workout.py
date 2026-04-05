from fastapi import APIRouter
from models.doymos_reader import bike_reader

router = APIRouter(prefix="/workout", tags=["workout"])

@router.get("/current")
def get_current():
    return {"start_date": bike_reader.start_date, "data": bike_reader.state }

@router.get("/plan")
def get_current():
    return bike_reader.today_get_plan()

@router.get("/stages/activate")
def set_active_stages():
    bike_reader.state.active_stages = True
    return {"start_date": bike_reader.start_date, "data": bike_reader.state}

@router.get("/stages/deactivate")
def set_deactivate_stages():
    bike_reader.state.active_stages = False
    return {"start_date": bike_reader.start_date, "data": bike_reader.state}
