from typing import List
from pydantic import BaseModel


#  datetime.today().isoweekday()
#  # 1=Monday, 7=Sunday

class Stage(BaseModel):
    duration: int
    resistance: int
    start_time: int = 0


class WorkPlan(BaseModel):
    id: int
    day_num: int
    stages: List[Stage]

    def __init__(self, id, day_num, stages):
        super().__init__(**{
            "id": id,
            "day_num": day_num,
            "stages": stages
        })
        self.calculate_times()

    def calculate_times(self):
        duration = 0
        for s in self.stages:
            s.start_time = duration
            duration += s.duration

    def get_stage_by_time(self, seconds):
        for s in self.stages:
            if s.start_time <= seconds < (s.start_time + s.duration):
                return s
        return None

WORK_PLANS = [
    WorkPlan(
        id=1,
        day_num=1,
        stages=[
            Stage(duration=40*60, resistance=4),
            Stage(duration=0, resistance=0),
        ]
    ),
    WorkPlan(
        id=2,
        day_num=7,
        stages=[
            Stage(duration=5 * 60, resistance=4),
            # 1
            Stage(duration=40, resistance=9),
            Stage(duration=90, resistance=3),
            # 2
            Stage(duration=40, resistance=9),
            Stage(duration=90, resistance=3),
            # 3
            Stage(duration=40, resistance=9),
            Stage(duration=90, resistance=3),
            # 4
            Stage(duration=40, resistance=9),
            Stage(duration=90, resistance=3),
            # 5
            Stage(duration=40, resistance=9),
            Stage(duration=90, resistance=3),
            # 6
            Stage(duration=40, resistance=9),
            Stage(duration=90, resistance=3),
            # 7
            Stage(duration=40, resistance=9),
            Stage(duration=90, resistance=3),
            # 8
            Stage(duration=40, resistance=9),
            Stage(duration=90, resistance=3),
            # 9
            Stage(duration=40, resistance=9),
            Stage(duration=90, resistance=3),
            # 10
            Stage(duration=40, resistance=9),
            Stage(duration=90, resistance=3),
            # rest
            Stage(duration=5 * 60, resistance=4),
            # end
            Stage(duration=0, resistance=0),
        ]
    ),
    WorkPlan(
        id=3,
        day_num=3,
        stages=[
            Stage(duration=50*60, resistance=4),
            Stage(duration=0, resistance=0),
        ]
    ),
    WorkPlan(
        id=3,
        day_num=4,
        stages=[
            Stage(duration=10 * 60, resistance=4),
            Stage(duration=10 * 60, resistance=6),
            Stage(duration=10 * 60, resistance=7),
            Stage(duration=5 * 60, resistance=4),
            Stage(duration=0, resistance=0),
        ]
    ),
    WorkPlan(
        id=4,
        day_num=5,
        stages=[
            Stage(duration=5 * 60, resistance=4),
            # 1
            Stage(duration=30, resistance=10),
            Stage(duration=90, resistance=3),
            # 2
            Stage(duration=30, resistance=10),
            Stage(duration=90, resistance=3),
            # 3
            Stage(duration=30, resistance=10),
            Stage(duration=90, resistance=3),
            # 4
            Stage(duration=30, resistance=10),
            Stage(duration=90, resistance=3),
            # 5
            Stage(duration=30, resistance=10),
            Stage(duration=90, resistance=3),
            # 6
            Stage(duration=30, resistance=10),
            Stage(duration=90, resistance=3),
            # rest
            Stage(duration=5 * 60, resistance=4),
            # end
            Stage(duration=0, resistance=0),
        ]
    ),
    WorkPlan(
        id=5,
        day_num=6,
        stages=[
            Stage(duration=40 * 60, resistance=3),
            Stage(duration=0, resistance=0),
        ]
    )
]