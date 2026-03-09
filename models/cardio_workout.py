from sqlalchemy import Column, Integer, Numeric, Text, DateTime, func, Computed
from sqlalchemy.orm import relationship
from config.database import AsyncSessionLocal
from models.base import Base
from models.bike_metric import BikeMetric
import logging

log = logging.getLogger(__name__)


class CardioWorkout(Base):
    __tablename__ = "cardio_workouts"
    __table_args__ = {"schema": "public"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    workout_date = Column(DateTime, nullable=False, server_default=func.now())
    type = Column(Text, nullable=False)
    distance_km = Column(Numeric(6, 2))
    duration_min = Column(Numeric(6, 2))
    avg_speed_kmh = Column(Numeric(5, 2))
    calories = Column(Integer)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    metrics = relationship("BikeMetric")


    async def create(self):
        self.calculate_averages()
        async with AsyncSessionLocal() as db:
            db.add(self)
            await db.flush()
            await db.commit()
            await db.refresh(self)

    def calculate_averages(self):
        if len(self.metrics) > 0 and self.metrics[-1].speed == 0:
            self.metrics.pop()
        idx = next((i for i in range(len(self.metrics) - 1, -1, -1) if self.metrics[i].speed != 0), None)
        self.distance_km = self.metrics[idx].distance
        self.avg_speed_kmh = sum(m.speed for m in self.metrics) / len(self.metrics)
        delta = self.metrics[idx].measured_at - self.metrics[0].measured_at
        self.duration_min = round((delta.total_seconds() - 10) / 60, 2)
        self.calories = self.metrics[idx].calories
        log.info(f"Distance {self.distance_km} km - Duration {self.duration_min} min - Speed {self.avg_speed_kmh} km/h")
        return True

    def add_metric(self, metric: BikeMetric):
        if metric.speed < 5:
            return "very-slow"
        if len(self.metrics) == 0:
            self.metrics.append(metric)
            return "added"
        # Get last
        last_metric = self.metrics[-1]
        if last_metric.same_values(metric):
            return "same"
        if last_metric.has_reset(metric):
            return "reset"
        self.metrics.append(metric)
        return "added"