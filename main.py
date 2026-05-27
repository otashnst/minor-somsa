import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

from backend.database.db import init_db
from backend.routes.orders import router as orders_router
from backend.routes.misc import branches_router, settings_router, logs_router
from backend.scheduler.jobs import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    # Start Telegram bot in background
    bot_token = os.getenv("BOT_TOKEN")
    if bot_token:
        from backend.telegram.bot import run_bot
        task = asyncio.create_task(run_bot())
    yield
    stop_scheduler()


app = FastAPI(title="Minor Somsa Dispatch", lifespan=lifespan)

app.include_router(orders_router)
app.include_router(branches_router)
app.include_router(settings_router)
app.include_router(logs_router)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


@app.get("/")
async def root():
    return FileResponse("frontend/index.html")
