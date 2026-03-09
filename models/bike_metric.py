from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class BikeMetric(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    idx: Optional[int] = None
    speed: Optional[float] = None
    distance: Optional[float] = None
    cadence: Optional[int] = None
    resistance: Optional[int] = None
    heart_rate: Optional[int] = None
    calories: Optional[int] = None
    measured_at: Optional[datetime] = None

    def same_values(self, metric):
        return (self.speed == metric.speed and self.distance == metric.distance and self.cadence == metric.cadence
                and self.calories == metric.calories and self.resistance == metric.resistance
                and self.heart_rate == metric.heart_rate)

    def has_reset(self, metric):
        return self.calories > metric.calories or self.distance > metric.distance