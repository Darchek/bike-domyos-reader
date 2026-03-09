import asyncio
import logging
import sys
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

@app.get("/init-seq", summary="Send init sequence")
async def init_sequence():
    await bike_reader.send_init_seq()
    return {"status": "sending sequence...", "timestamp": datetime.now().isoformat()}

@app.get("/send-display-seq", summary="Send display")
async def send_display():
    await bike_reader.send_display()
    return {"status": "Send display", "timestamp": datetime.now().isoformat()}


app.include_router(workout_router)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    if len(sys.argv) > 1 and sys.argv[1] == "--prod":
        log.info("Starting production server...")
        uvicorn.run(app, host=settings.HOST, port=settings.DEV_PORT, reload=False)
    else:
        log.info("Starting development server...")
        uvicorn.run(app, host=settings.HOST, port=settings.DEV_PORT, reload=False)