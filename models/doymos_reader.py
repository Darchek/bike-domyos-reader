import asyncio
import math
import time
from datetime import datetime
from typing import Optional
from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from config.settings import get_settings
import logging

from models.passive_scanner import PassiveScanner

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

class WorkoutState:

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
        }


# ── Packet parser ─────────────────────────────────────────────────────────────

def parse_packet(data: bytes, state: WorkoutState) -> bool:
    """Parse a 26-byte notification from the machine."""
    if len(data) != 26:
        return False
    state.packets += 1
    state.speed_kmh     = ((data[6] << 8) | data[7]) / 10.0
    state.cadence_rpm   = data[9] if data[9] > 0 else 0
    state.calories_kcal = (data[10] << 8) | data[11]
    state.distance_km   = ((data[12] << 8) | data[13]) / 10.0
    res = data[14]
    if 1 <= res <= 15:
        state.resistance = res
    state.heart_rate = data[18]
    incl = data[21]
    if 0 <= incl <= 15:
        state.inclination = incl
    btn = data[22]
    state.button = "▲ Incline UP" if btn == 0x06 else ("▼ Incline DOWN" if btn == 0x07 else "")
    state.watts = state.calc_watts()
    return True


# ── Display packets  (machine screen keep-alive) ──────────────────────────────

def _checksum(buf: bytearray) -> int:
    """Sum of all bytes mod 256, as used by the machine firmware."""
    return sum(buf) & 0xFF

def build_display_packets(state: WorkoutState) -> list[tuple[bytes, bytes]]:
    """
    Build the two display-update write packets that keep the machine screen alive.
    Each is 27 bytes, split into (first 20, last 7) due to BLE MTU.
    Mirrors updateDisplay() in domyoselliptical.cpp exactly.

    Strategy: start from the exact default byte arrays used in the source,
    then assign only the fields the source assigns. Every other byte keeps
    its default value — this avoids off-by-one errors from manual counting.

    Returns: [(pkt_a_part1, pkt_a_part2), (pkt_b_part1, pkt_b_part2)]
    """
    elapsed = state.elapsed_s

    # ── Packet A  (0xf0 0xcd)  –  odometer / distance ────────────────────────
    # Source default:
    #   {0xf0,0xcd,0x01, 0x00,0x00, 0x01, 0xff×20, 0x00}
    # display2[3-4] = (uint16_t)(odometer() * 10)  → tenths of km, big-endian
    dist_raw = int(state.distance_km * 10) & 0xFFFF
    a = bytearray([0xf0, 0xcd, 0x01, 0x00, 0x00, 0x01, 0xff, 0xff, 0xff, 0xff,
                   0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
                   0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00])
    a[3] = (dist_raw >> 8) & 0xFF
    a[4] =  dist_raw       & 0xFF
    a[26] = _checksum(a[:26])

    # ── Packet B  (0xf0 0xcb)  –  time / speed / HR / cadence / calories ─────
    # Source default:
    #   {0xf0,0xcb,0x03, 0x00,0x00, 0xff, 0x01, 0x00,0x00, 0x02,0x01,0x00,
    #    0x00, 0x00, 0x01,0x00, 0x00, 0x01,0x01, 0x00,0x00, 0x01,
    #    0xff,0xff,0xff,0xff, 0x00}
    #
    # Fields assigned by source (index → meaning):
    #   [3]  = elapsed // 60        (minutes)
    #   [4]  = elapsed %  60        (seconds)
    #   [7]  = (uint16_t)speed >> 8 (speed hi — plain int km/h, NOT *10)
    #   [8]  = (uint16_t)speed & FF  (speed lo)
    #   [12] = heart_rate
    #   [16] = cadence
    #   [19] = calories >> 8        (calories hi)
    #   [20] = calories & FF        (calories lo)
    #   [26] = checksum
    speed_raw = int(state.speed_kmh) & 0xFFFF  # plain integer km/h, e.g. 8 not 82
    cal_raw   = state.calories_kcal  & 0xFFFF

    b = bytearray([0xf0, 0xcb, 0x03, 0x00, 0x00, 0xff, 0x01, 0x00, 0x00, 0x02,
                   0x01, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x01, 0x01, 0x00,
                   0x00, 0x01, 0xff, 0xff, 0xff, 0xff, 0x00])
    b[3]  = (elapsed // 60) & 0xFF
    b[4]  = (elapsed %  60) & 0xFF
    b[7]  = (speed_raw >> 8) & 0xFF
    b[8]  =  speed_raw       & 0xFF
    b[12] = state.heart_rate  & 0xFF
    b[16] = state.cadence_rpm & 0xFF
    b[19] = (cal_raw >> 8) & 0xFF
    b[20] =  cal_raw        & 0xFF
    b[26] = _checksum(b[:26])

    # Split each 27-byte packet into (first 20 bytes, last 7 bytes)
    return [
        (bytes(a[:20]), bytes(a[20:])),
        (bytes(b[:20]), bytes(b[20:])),
    ]


# ── Display (terminal) ────────────────────────────────────────────────────────

def print_dashboard(state: WorkoutState):
    h, rem = divmod(state.elapsed_s, 3600)
    m, s   = divmod(rem, 60)
    elapsed_str = f"{h:02d}:{m:02d}:{s:02d}"
    print(
        f"\r⏱ {elapsed_str} | "
        f"spd:{state.speed_kmh:4.1f}km/h | "
        f"cad:{state.cadence_rpm:3d}rpm | "
        f"pwr:{state.watts:5.0f}W | "
        f"hr:{state.heart_rate:3d}bpm | "
        f"res:{state.resistance:2d}/15 | "
        f"incl:{state.inclination:2d}/15 | "
        f"dist:{state.distance_km:.2f}km | "
        f"cal:{state.calories_kcal:4d}kcal",
        end="", flush=True,
    )

# ── Main reader ───────────────────────────────────────────────────────────────

class DomyosReader:

    def __init__(self):
        self.address  = get_settings().DOMYOS_BIKE_ADDRESS
        self.state    = WorkoutState()
        self._start:      Optional[float] = None
        self._client:     Optional[BleakClient] = None
        self._display_tick = 0   # counts 300ms ticks; send display every ~1 s (tick 3)
        self._scanner: PassiveScanner | None = None
        self.workout = []

    def _on_notify(self, char: BleakGATTCharacteristic, data: bytearray):
        raw = bytes(data)
        if len(raw) != 26:
            return
        if self._start:
            self.state.elapsed_s = int(time.time() - self._start)
        if not parse_packet(raw, self.state):
            return

        # State
        if self.state.speed_kmh == 0.0 and self._scanner.status != 'idle':
            self._scanner.set_idle()
            log.info("State is idle!")
        elif self.state.speed_kmh > 0.0 and self._scanner.status != 'running':
            self._scanner.set_running()

        self.workout.append(self.state)
        # print_dashboard(self.state)

        print(f"_on_notify -> Speed {self.state.speed_kmh} - Distance: {self.state.distance_km}", len(self.workout))


        # loop = asyncio.get_event_loop()
        # loop.create_task(self._client.write_gatt_char(get_settings().DOMYOS_WRITE, raw, response=False))

    async def _send_display(self):
        """
        Send both display packets to keep the machine screen alive.
        Called once per second.

        Each 27-byte packet is split into two chunks (20 + 7 bytes) to respect
        the BLE MTU, exactly as QZ does.

        Write pacing mirrors QZ's writeCharacteristic():
          - first chunk:  response=False  (fire-and-forget, fast)
          - second chunk: response=True   (waits for GATT write-ack before continuing)
        A short sleep after each full packet gives the machine time to process
        and update its display before the next packet arrives.
        """
        if self._client is None or not self._client.is_connected:
            return
        for part1, part2 in build_display_packets(self.state):
            await self._client.write_gatt_char(get_settings().DOMYOS_WRITE, part1, response=False)
            await self._client.write_gatt_char(get_settings().DOMYOS_WRITE, part2, response=True)
            await asyncio.sleep(0.05)  # let machine digest before next packet

    async def run(self):

        log.info(f"\n🔗  Connecting to {self.address} …")

        async with BleakClient(self.address, timeout=15.0) as client:
            self._client = client
            log.info(f"✅  Connected (MTU {client.mtu_size})")

            service_uuids = [s.uuid for s in client.services]
            if get_settings().DOMYOS_SERVICE not in service_uuids:
                log.info("\n⚠️  Domyos UART service not found. Available services:")
                for svc in client.services:
                    log.info(f"   {svc.uuid}  {svc.description}")
                return

            await client.start_notify(get_settings().DOMYOS_NOTIFY, self._on_notify)
            log.info("📬  Subscribed to notify characteristic")

            log.info("🔧  Sending init sequence…")
            for pkt in INIT_SEQ:
                await client.write_gatt_char(get_settings().DOMYOS_WRITE, pkt, response=False)
                await asyncio.sleep(0.05)

            # Send an initial display update immediately so screen never blanks
            await self._send_display()
            self._start = time.time()
            log.info("✅  Ready — screen + Python both active")

            while client.is_connected:
                await asyncio.sleep(0.5)

        log.info(f"Workout has ended. Total packets {self.state.packets}")
        self._scanner.set_stopped()
        self._client = None
        self._summary()

    def _summary(self):
        s = self.state
        h, rem = divmod(s.elapsed_s, 3600)
        m, sec = divmod(rem, 60)
        text = f"\n{'─'*48}"
        text += f"📊  Session Summary"
        text += f"{'─'*48}"
        text += f"  Duration   : {h:02d}:{m:02d}:{sec:02d}"
        text += f"  Distance   : {s.distance_km:.2f} km"
        text += f"  Calories   : {s.calories_kcal} kcal"
        text += f"  Packets    : {s.packets}"
        text += f"  Last speed : {s.speed_kmh:.1f} km/h"
        text += f"  Last cad.  : {s.cadence_rpm} rpm"
        text += f"  Last power : {s.watts:.0f} W"
        text += f"  Last HR    : {s.heart_rate} bpm"
        text += f"{'─'*48}"
        log.info(text)

    async def start_scanner(self):
        self._scanner = PassiveScanner(self.start_reader)
        await self._scanner.start()

    async def start_reader(self):
        await self.run()


bike_reader = DomyosReader()