import json

from models.bike_metric import BikeMetric
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
import logging

log = logging.getLogger(__name__)


class CardioWorkout(BaseModel):
    id: Optional[int] = None
    created_at: Optional[datetime] = datetime.now()
    workout_date: Optional[datetime] = datetime.now()
    type: str = 'cycling'
    distance_km: Optional[float] = None
    duration_min: Optional[float] = None
    avg_speed_kmh: Optional[float] = None
    calories: Optional[int] = None
    notes: Optional[str] = None

    metrics: List[BikeMetric] = []

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

    def save_cardio_file(self):
        try:
            date_str = datetime.today().strftime("%Y_%m_%d")
            with open(f"files/session_{date_str}.json", "w") as f:
                f.write(json.dumps(self.model_dump(mode="json")))
        except Exception as e:
            log.error(f"Error when saving file. Error: {e}")