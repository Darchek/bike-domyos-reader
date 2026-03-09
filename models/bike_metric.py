from sqlalchemy import Column, Integer, Numeric, Text, DateTime, func, Computed, ForeignKey
from config.database import AsyncSessionLocal
from models.base import Base


class BikeMetric(Base):
    __tablename__ = "bike_metrics"
    __table_args__ = {"schema": "public"}

    session_id = Column(Integer, ForeignKey("public.cardio_workouts.id"), primary_key=True)
    idx = Column(Integer, primary_key=True)
    measured_at = Column(DateTime, server_default=func.now())
    speed = Column(Numeric(5, 2))
    distance = Column(Numeric(5, 2))
    cadence = Column(Integer)
    calories = Column(Integer)
    resistance = Column(Integer)
    heart_rate = Column(Integer)

    def same_values(self, metric):
        return (self.speed == metric.speed and self.distance == metric.distance and self.cadence == metric.cadence
                and self.calories == metric.calories and self.resistance == metric.resistance
                and self.heart_rate == metric.heart_rate)

    def has_reset(self, metric):
        return self.calories > metric.calories or self.distance > metric.distance