import json
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import logging.config
from ..api.wotb import APIServer
from ..models import User
from .auth import router as auth_router
from .api_player import router as player_router, stats as player_stats
from .api_socket import player_router_socket
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ..interfase.player import PlayerSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    trigger = CronTrigger(hour=16, minute=24, second=30)
    scheduler.add_job(PlayerSession.update_db, trigger=trigger)

    scheduler.start()
    yield
    print("Waiting for the database update to complete before shutting down...")
    scheduler.shutdown(wait=False)  # Ожидаем завершения всех задач


app = FastAPI(title="Authentication", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(player_router)
app.include_router(player_stats)
# app.include_router(player_router_socket)

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
