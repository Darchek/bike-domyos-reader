from pydantic import BaseModel
from typing import Optional, List


class PolarData(BaseModel):
    avg_hr_bpm: Optional[int] = None
    hr_bpm: Optional[int] = None
    sensor_contact: Optional[bool] = False
    rr_intervals_ms: Optional[List[float]] = None

    def __init__(self, avg_hr_bpm, sensor_contact, rr_intervals_ms):
        super().__init__()
        self.avg_hr_bpm = avg_hr_bpm
        self.sensor_contact = sensor_contact
        self.rr_intervals_ms = rr_intervals_ms
        self.hr_bpm = self.calculate_instant_hr()

    def calculate_instant_hr(self):
        if self.rr_intervals_ms:
            return round(60000 / self.rr_intervals_ms[-1])
        else:
            return self.avg_hr_bpm
