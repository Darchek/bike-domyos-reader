import requests
from config.settings import get_settings
import logging

log = logging.getLogger(__name__)


class HttpClient:

    @staticmethod
    async def start_bike_session():
        try:
            response = requests.get(f"{get_settings().BACKEND_URL}/bike/start", timeout=5)
            data = response.json()
            log.info(data)
            return True
        except Exception as e:
            log.error(f"Request error: {e}")
            return False

    @staticmethod
    async def end_bike_session(payload):
        try:
            response = requests.post(f"{get_settings().BACKEND_URL}/bike", json=payload, timeout=10)
            data = response.json()
            log.info(f"Bike session registered successfully. ID: {data['id']}")
            return True
        except Exception as e:
            log.error(f"Request error: {e}")
            return False

    @staticmethod
    async def turn_on_fan():
        try:
            response = requests.post(f"{get_settings().HOMEASSISTANT_WEBHOOK_URL}/"
                                     f"{get_settings().HA_TURN_ON_FAN_PATH}", verify=False, timeout=10)
            log.info(f"Fan on!")
            return True
        except Exception as e:
            log.error(f"Request error: {e}")
            return False


