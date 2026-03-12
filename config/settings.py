from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # N8N
    BACKEND_URL: str = ""

    # DATABASE
    DATABASE_URL: str = ""

    # BLE Device
    DOMYOS_BIKE_ADDRESS: str = ""
    POLAR_SENSOR_ADDRESS: str = ""

    # BLE Characteristic UUIDs
    DOMYOS_SERVICE: str = "49535343-fe7d-4ae5-8fa9-9fafd205e455"
    DOMYOS_NOTIFY: str = "49535343-1e4d-4bd9-ba61-23c647249616"
    DOMYOS_WRITE: str = "49535343-8841-43f4-a8d4-ecbe34729bb3"

    # BLE Polar Sensor
    POLAR_NOTIFY: str = "00002a37-0000-1000-8000-00805f9b34fb"
    POLAR_BATTERY: str = "00002a19-0000-1000-8000-00805f9b34fb"

    # Server
    HOST: str = "0.0.0.0"
    DEV_PORT: int = 8000
    PROD_PORT: int = 8001

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — loaded once at startup."""
    return Settings()