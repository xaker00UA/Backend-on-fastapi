from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
from .auth import router as auth_router
from .api_player import router as player_router, stats as player_stats
from .api_clan.api_clan import router as clan_router
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ..interfase.player import PlayerSession
from ..interfase.clan import ClanInterface
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "app.log", encoding="utf-8", maxBytes=10 * 1024 * 1024, backupCount=5
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
debug_handler = RotatingFileHandler(
    "debug.log", encoding="utf-8", maxBytes=10 * 1024 * 1024, backupCount=5
)
logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    trigger = CronTrigger(hour=12, minute=00, second=00)
    trigger_clan = CronTrigger(week=1, day_of_week="mon", hour=12, minute=00)
    scheduler.add_job(PlayerSession.update_db, trigger=trigger)
    scheduler.add_job(ClanInterface.update_db, trigger=trigger_clan)
    print("Starting the scheduler...")
    scheduler.start()
    yield
    print("Waiting for the database update to complete before shutting down...")
    scheduler.shutdown(wait=True)  # Ожидаем завершения всех задач


app = FastAPI(title="Authentication", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(player_router)
app.include_router(player_stats)
app.include_router(clan_router)


origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root(request: Request):

    return {"message": "you is root"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        access_log=True,  # Включает логи запросов uvicorn
    )
