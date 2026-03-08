import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from config.settings import get_settings
from models.doymos_reader import bike_reader
from routes.workout import router as workout_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FastAPI lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(bike_reader.start_scanner())
    log.info("BLE background task started.")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        log.info("BLE background task stopped.")

app = FastAPI(
    title="Bike BLE Server",
    description="Passive BLE listener + REST API for your elliptical bike",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", summary="Server health check")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


app.include_router(workout_router)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, reload=False)