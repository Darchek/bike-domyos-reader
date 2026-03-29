from datetime import datetime

from fastapi import APIRouter
from models.doymos_reader import bike_reader
from models.work_plan import WORK_PLANS

router = APIRouter(prefix="/workout", tags=["workout"])


@router.get("/current")
def get_current():
    return bike_reader.state


@router.get("/plan")
def get_current():
    day_num = datetime.today().isoweekday()
    day_num = 1
    d = [wp for wp in WORK_PLANS if day_num == wp.day_num]
    if len(d) > 0:
        return d[0]
    return None