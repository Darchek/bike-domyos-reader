import asyncio
from bleak import BleakScanner

from config.http_client import HttpClient
from config.settings import get_settings
import logging

log = logging.getLogger(__name__)


class PassiveScanner:

    def __init__(self, start_reader):
        self.status = "stopped"
        self.start_reader = start_reader

    async def detection_callback(self, device, advertisement_data):
        if device.address == get_settings().DOMYOS_BIKE_ADDRESS and self.status == "stopped":
            log.info(f"Bike detected: {device.address}")
            self.set_running()
            asyncio.create_task(HttpClient.start_bike_session())
            await self.start_reader(device)

    async def start(self):
        scanner = BleakScanner(self.detection_callback)
        await scanner.start()
        # await asyncio.Event().wait()  # run forever

    def set_idle(self):
        self.status = "idle"

    def set_running(self):
        self.status = "running"

    def set_stopped(self):
        self.status = "stopped"