import asyncio
import json
import os.path

from fastapi import APIRouter

from config.http_client import HttpClient
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


@router.get("/resend/{date}")
async def resend_by_date(date):
    path = f"files/session_{date[0:4]}_{date[4:6]}_{date[6:8]}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
            await HttpClient.end_bike_session(data)
            return data
    return f"File {path} do not exist"