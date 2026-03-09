from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_db
from models.cardio_workout import CardioWorkout
from models.doymos_reader import bike_reader

router = APIRouter(prefix="/workout", tags=["workout"])



@router.get("/current")
def get_current():
    return bike_reader.state



@router.get("/sessions")
async def get_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CardioWorkout))
    workouts = result.scalars().all()
    return workouts


@router.get("/create")
async def get_sessions(db: AsyncSession = Depends(get_db)):
    cw = CardioWorkout(
        type="cycling",
        distance_km=10,
        duration_min=23,
        calories=10
    )
    await cw.create()
    return cw
