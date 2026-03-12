import asyncio
from typing import Optional
from bleak import BleakClient, BleakScanner
from config.settings import get_settings
from models.polar_data import PolarData
import logging

log = logging.getLogger(__name__)

class PolarReader:

    def __init__(self):
        self.device = None
        self._client: Optional[BleakClient] = None
        self.status = "stopped"
        self.data: PolarData | None = None
        self.count = 0

    def get_heart_rate(self):
        if not self.data:
            return 0
        if not self.data.hr_bpm:
            return 0
        return self.data.hr_bpm

    def parse_hr(self, data: bytearray) -> PolarData:
        """Parse Heart Rate Measurement characteristic (spec: GATT 0x2A37)."""
        flags = data[0]
        hr_format_16bit = flags & 0x01  # bit 0: 0 = uint8, 1 = uint16
        sensor_contact = (flags >> 1) & 0x03
        energy_expended_present = (flags >> 3) & 0x01
        rr_intervals_present = (flags >> 4) & 0x01

        idx = 1
        if hr_format_16bit:
            hr = int.from_bytes(data[idx:idx + 2], "little")
            idx += 2
        else:
            hr = data[idx]
            idx += 1

        rr_intervals = []
        if energy_expended_present:
            idx += 2  # skip energy expended (uint16)
        if rr_intervals_present:
            while idx + 1 < len(data):
                rr = int.from_bytes(data[idx:idx + 2], "little") / 1024 * 1000  # ms
                rr_intervals.append(round(rr, 1))
                idx += 2

        self.data = PolarData(hr, bool(sensor_contact & 0x02), rr_intervals)
        return self.data

    def _on_notify(self, sender, data: bytearray):
        polar = self.parse_hr(data)
        if self.count % 40 == 0:
            log.info(f"Instant HR: {polar.hr_bpm} bpm  (sensor avg: {polar.avg_hr_bpm} bpm) - contact: {polar.sensor_contact}")
        self.count += 1

    async def run(self):
        address = get_settings().POLAR_SENSOR_ADDRESS
        try:
            log.info(f"\n🔗  Connecting to {address} …")
            async with BleakClient(self.device, timeout=15.0) as client:
                self._client = client
                log.info(f"✅  Connected (MTU {client.mtu_size})")

                battery = await client.read_gatt_char(get_settings().POLAR_BATTERY)
                log.info(f"Battery: {battery[0]}%")

                await client.start_notify(get_settings().POLAR_NOTIFY, self._on_notify)
                log.info("📬  Subscribed to notify characteristic")

                while client.is_connected:
                    await asyncio.sleep(0.5)
            log.info("Polar sensor disconnected. Bye...")
            self.status = "stopped"
        except Exception as e:
            log.error(f"Error when connecting to bluetooth client: {e}")
            if self.status == "running":
                await self.run()

    async def start_scanner(self):
        logging.info("Scanning for polar sensor device...")
        await self.start()

    async def detection_callback(self, device, advertisement_data):
        if (device.name
                and device.address == get_settings().POLAR_SENSOR_ADDRESS
                and "Polar" in device.name
                and self.status == "stopped"):
            self.status = "running"
            self.device = device
            log.info(f"Polar detected: {device.address}")
            # await self.polar_connection()
            await self.run()

    async def start(self):
        scanner = BleakScanner(self.detection_callback)
        await scanner.start()
        await asyncio.Event().wait()


if __name__ == "__main__":
    polar_reader = PolarReader()
    task = asyncio.run(polar_reader.start_scanner())