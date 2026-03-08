import requests
from bleak import BleakScanner
from config.settings import get_settings
import logging

log = logging.getLogger(__name__)


class PassiveScanner:

    def __init__(self, start_reader):
        self.status = "stopped"
        self.start_reader = start_reader

    def send_notification(self):
        response = requests.get(get_settings().N8N_WEBHOOK_URL)
        data = response.json()
        log.info(data)
        return True

    async def detection_callback(self, device, advertisement_data):
        if device.address == get_settings().DOMYOS_BIKE_ADDRESS and self.status == "stopped":
            log.info(f"Bike detected: {device.address}")
            self.set_running()
            self.send_notification()
            await self.start_reader()

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