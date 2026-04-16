import asyncio
import math
import time
from datetime import datetime, timezone
from typing import Optional
from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from config.http_client import HttpClient
from config.settings import get_settings
import logging

from models.bike_metric import BikeMetric
from models.cardio_workout import CardioWorkout
from models.passive_scanner import PassiveScanner
from models.play_tone import play_sound
from models.polar_reader import PolarReader
from models.work_plan import WORK_PLANS

log = logging.getLogger(__name__)

# ── Init sequence  (btinit_changyow, startTape=False) ─────────────────────────
INIT_SEQ = [
    bytes([0xf0, 0xc8, 0x01, 0xb9]),
    bytes([0xf0, 0xc9, 0xb9]),
    bytes([0xf0, 0xa3, 0x93]),
    bytes([0xf0, 0xa4, 0x94]),
    bytes([0xf0, 0xa5, 0x95]),
    bytes([0xf0, 0xab, 0x9b]),
    bytes([0xf0, 0xc4, 0x03, 0xb7]),
    bytes([0xf0, 0xad, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
           0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x01, 0xff]),
    bytes([0xff, 0xff, 0x8b]),
    bytes([0xf0, 0xcb, 0x02, 0x00, 0x08, 0xff, 0xff, 0xff, 0xff, 0xff,
           0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x01, 0x00]),
    bytes([0x00, 0x01, 0xff, 0xff, 0xff, 0xff, 0xb6]),
    bytes([0xf0, 0xad, 0xff, 0xff, 0x00, 0x05, 0xff, 0xff, 0xff, 0xff,
           0xff, 0xff, 0xff, 0x00, 0x00, 0xff, 0xff, 0xff, 0x01, 0xff]),
]

NOOP = bytes([0xf0, 0xac, 0x9c])

# ── Workout state ─────────────────────────────────────────────────────────────

class WorkoutState_DEPRECATED:

    def __init__(self):
        self.speed_kmh:     float = 0.0
        self.cadence_rpm:   int   = 0
        self.resistance:    int   = 0     # 1-15
        self.inclination:   int   = 0     # 0-15
        self.heart_rate:    int   = 0
        self.calories_kcal: int   = 0
        self.distance_km:   float = 0.0
        self.watts:         float = 0.0
        self.button:        str   = ""
        self.elapsed_s:     int   = 0
        self.packets:       int   = 0
        self.active_stages: bool  = True

    def calc_watts(self) -> float:
        """Exact formula from domyoselliptical.cpp::watts()"""
        if self.cadence_rpm <= 0 or self.resistance <= 0:
            return 0.0
        return (10.39 + 1.45 * (self.resistance - 1.0)) * math.exp(0.028 * self.cadence_rpm)

    def to_dict(self) -> dict:
        return {
            "timestamp":   datetime.now().isoformat(timespec="seconds"),
            "speed_kmh":   round(self.speed_kmh, 1),
            "cadence_rpm": self.cadence_rpm,
            "resistance":  self.resistance,
            "inclination": self.inclination,
            "heart_rate":  self.heart_rate,
            "calories":    self.calories_kcal,
            "distance_km": round(self.distance_km, 2),
            "watts":       round(self.watts, 1),
            "elapsed_s":   self.elapsed_s,
            "active_stages": self.active_stages
        }


# ── Display packets  (machine screen keep-alive) ──────────────────────────────

def _checksum(buf: bytearray) -> int:
    """Sum of all bytes mod 256, as used by the machine firmware."""
    return sum(buf) & 0xFF

# ── Main reader ───────────────────────────────────────────────────────────────

class DomyosReader:

    CONNECTION_ELAPSED_TIME = 5

    def __init__(self):
        self.device = None
        self.start_date = None
        self.state = BikeMetric()
        self._start: Optional[float] = None
        self._client: Optional[BleakClient] = None
        self._display_tick = 0   # counts 300ms ticks; send display every ~1 s (tick 3)
        self._scanner: PassiveScanner | None = None
        self._polar: PolarReader | None = None
        self.cardio = None
        self.plan = None
        self.session_end = False

    def parse_packet(self, data: bytes) -> BikeMetric | None:
        """Parse a 26-byte notification from the machine."""
        if len(data) != 26:
            return None
        metric = BikeMetric()
        metric.idx = len(self.cardio.metrics) + 1
        metric.speed = ((data[6] << 8) | data[7]) / 10.0
        metric.cadence = data[9] if data[9] > 0 else 0
        metric.calories = (data[10] << 8) | data[11]
        metric.distance = ((data[12] << 8) | data[13]) / 10.0
        metric.measured_at = datetime.now()
        res = data[14]
        if 1 <= res <= 15:
            metric.resistance = res
        metric.heart_rate = self._polar.get_heart_rate()
        metric.elapsed_s = time.time() - self._start
        metric.active_stages = self.state.active_stages
        # metric.heart_rate = data[18]
        # incl = data[21]
        # if 0 <= incl <= 15:
        #     state.inclination = incl
        # btn = data[22]
        # state.button = "▲ Incline UP" if btn == 0x06 else ("▼ Incline DOWN" if btn == 0x07 else "")
        # state.watts = state.calc_watts()
        self.state = metric
        return metric

    async def _on_notify(self, char: BleakGATTCharacteristic, data: bytearray):
        raw = bytes(data)
        if len(raw) != 26:
            return
        bike_metric = self.parse_packet(raw)
        if not bike_metric:
            return

        if self.state.active_stages:
            await self.manage_stages()

        # State
        if bike_metric.speed == 0.0 and self._scanner.status != 'idle':
            self._scanner.set_idle()
            log.info("State is idle!")
        elif bike_metric.speed > 0.0 and self._scanner.status != 'running':
            self._scanner.set_running()

        res = self.cardio.add_metric(bike_metric)
        if res == "added":
            log.info(f"Speed {bike_metric.speed} - Distance: {bike_metric.distance} - "
                     f"Heart rate: {bike_metric.heart_rate} - Calories: {bike_metric.calories}")

        # loop = asyncio.get_event_loop()
        # loop.create_task(self._client.write_gatt_char(get_settings().DOMYOS_WRITE, raw, response=False))

    async def send_init_seq(self):
        await asyncio.sleep(0.5)
        log.info("🔧  Sending init sequence…")
        for idx, pkt in enumerate(INIT_SEQ):
            await self._client.write_gatt_char(get_settings().DOMYOS_WRITE, pkt, response=True)
            await asyncio.sleep(0.05)

    async def run(self):
        address = get_settings().DOMYOS_BIKE_ADDRESS
        first_time = time.time()
        try:
            log.info(f"\n🔗  Connecting to {address} …")
            async with BleakClient(self.device, timeout=15.0) as client:
                self._client = client
                log.info(f"✅  Connected (MTU {client.mtu_size})")

                service_uuids = [s.uuid for s in client.services]
                if get_settings().DOMYOS_SERVICE not in service_uuids:
                    log.info("\n⚠️  Domyos UART service not found. Available services:")
                    for svc in client.services:
                        log.info(f"   {svc.uuid}  {svc.description}")
                    return
                self.session_end = False
                self.today_get_plan()
                elapsed = time.time() - first_time
                wait_time = self.CONNECTION_ELAPSED_TIME - elapsed
                log.info("Elapsed time for connection: {0:.2f}s -  Waiting time: {1:.2f}s".format(elapsed, wait_time))
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

                self.start_date = datetime.now(timezone.utc)
                self._start = time.time()
                await client.start_notify(get_settings().DOMYOS_NOTIFY, self._on_notify)
                log.info("📬  Subscribed to notify characteristic")
                await self.send_init_seq()

                # Send an initial display update immediately so screen never blanks
                log.info("✅  Ready — screen + Python both active")

                while client.is_connected:
                    await asyncio.sleep(0.5)

            log.info(f"Workout has ended. Total packets {len(self.cardio.metrics)}")
            await self.save_workout()
            self._scanner.set_stopped()
            self._client = None
            self.session_end = False
            self.cardio = CardioWorkout()
        except Exception as e:
            log.error(f"Error when connecting to bluetooth client: {e}")

    async def save_workout(self):
        if len(self.cardio.metrics) > 10 and self.cardio.metrics[-1].distance > 2:
            self.cardio.calculate_averages()
            self.cardio.save_cardio_file()
            asyncio.create_task(HttpClient.end_bike_session(self.cardio.model_dump(mode="json")))
        else:
            log.info(f"Discarding cardio distance is less than 2 km. "
                     f"Metrics {len(self.cardio.metrics)} - Distance: {self.cardio.metrics[-1].distance} km")

    async def start_bike_scanner(self):
        self._scanner = PassiveScanner(self.start_reader)
        await self._scanner.start()

    async def start_polar_scanner(self):
        self._polar = PolarReader()
        await self._polar.start()

    async def start_reader(self, device=None):
        self.device = device
        self.cardio = CardioWorkout()
        await self.run()

    # RESISTANCE

    async def manage_stages(self):
        if self.session_end:
            return True
        stage = self.plan.get_stage_by_time(self.state.elapsed_s)
        if not stage:
            log.info(f"Stages completed! {self.state.elapsed_s}")
            self.session_end = True
            play_sound()
            return True
        if self.state.resistance == stage.resistance:
            return True
        await self.change_resistance(stage.resistance)
        return True

    async def change_resistance(self, target_level: int):
        current_resistance = self.state.resistance
        diff_level = target_level - current_resistance
        if diff_level == 0:
            log.info(f"Resistance {target_level} archive successfully")
        elif diff_level > 0:
            log.info(f"INCREASE --- Sending resistance directly to {target_level}")
            await self.increase_resistance(target_level)
        elif diff_level < 0:
            log.info(f"DECREASE --- Sending resistance directly to {target_level}")
            await self.decrease_resistance(target_level)

    async def force_resistance(self, level: int):
        """
        Send a resistance command to the Domyos bike.

        Args:
            level: Resistance level 1-15
        """
        if self._client is None or not self._client.is_connected:
            log.warning("Cannot set resistance: not connected")
            return

        level = max(1, min(15, level))  # clamp to valid range

        # Build the 23-byte resistance packet (from qdomyos-zwift forceResistance)
        pkt = bytearray([
            0xf0, 0xad, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00, 0x01, 0xff,
            0xff, 0xff, 0x00
        ])

        pkt[10] = level  # resistance value at byte index 10

        # Checksum: sum of bytes 0..21, mod 256
        pkt[22] = sum(pkt[:22]) & 0xFF

        # Split into two writes (20 + 3) just like QZ does
        write_uuid = get_settings().DOMYOS_WRITE
        await self._client.write_gatt_char(write_uuid, bytes(pkt[:20]), response=True)
        await self._client.write_gatt_char(write_uuid, bytes(pkt[20:]), response=True)

        log.info(f"🎚️  Resistance set to {level}")

    async def increase_resistance(self, target_level=None):
        current = self.state.resistance if self.state.resistance > 0 else 1
        target_level = target_level if target_level else current + 1
        await self.force_resistance(target_level)

    async def decrease_resistance(self, target_level=None):
        """Decrease resistance by 1 (min 1)."""
        target_level = target_level if target_level else self.state.resistance - 1
        await self.force_resistance(target_level)

    # WORKOUT PLAN

    def today_get_plan(self):
        day_num = datetime.today().isoweekday()
        d = [wp for wp in WORK_PLANS if day_num == wp.day_num]
        if len(d) > 0:
            self.plan = d[0]
            return d[0]
        return None




bike_reader = DomyosReader()