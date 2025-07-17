from math import e
import time
import traceback
from typing import Callable
import warnings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware


from fastapi.responses import JSONResponse, RedirectResponse

from utils.models.response_model import ErrorResponse
from .auth import router as auth_router
from .api_player import router as player_router, stats as player_stats
from .api_clan.api_clan import router as clan_router
from .admin.admin import router as admin_router
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ..interface.player import PlayerSession
from ..interface.clan import ClanInterface
from ..database.admin import initialize_db
from .middleware import ExceptionLoggingMiddleware
from ..error.exception import *
from ..settings.logger import LoggerFactory
from ..api.wotb import APIServer


from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    initialize_db()
    app.state.scheduler = scheduler
    app.state.time = time.time()
    server = APIServer()
    await server.init_session()
    trigger = CronTrigger(hour=12, minute=10, second=00)
    trigger_clan = CronTrigger(day_of_week="mon", hour=12, minute=10)
    scheduler.add_job(
        PlayerSession.update_db, trigger=trigger, misfire_grace_time=3600 * 6
    )
    scheduler.add_job(
        ClanInterface.update_db, trigger=trigger_clan, misfire_grace_time=3600 * 6
    )
    scheduler.add_job(
        PlayerSession.update_player_token,
        trigger=trigger_clan,
        misfire_grace_time=3600 * 6,
    )
    LoggerFactory.log("Start scheduler job")
    scheduler.start()
    yield
    await server.close()
    LoggerFactory.log(
        "Waiting for the database update to complete before shutting down..."
    )
    scheduler.shutdown(wait=True)  # Ожидаем завершения всех задач


origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
mid = [
    Middleware(ExceptionLoggingMiddleware),
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
]


app = FastAPI(
    title="Authentication",
    lifespan=lifespan,
    servers=[
        {"url": "http://localhost:8000", "description": "Local server API"},
        {"url": "http://testserver.ua/api", "description": "Latest server API"},
        {"url": "http://wotblstatic.com/api", "description": "Prod server API"},
    ],
    middleware=mid,
    responses={
        code: {"model": ErrorResponse, "description": msg}
        for _, (code, msg) in EXCEPTION_HANDLERS.items()
    },
)
app.include_router(auth_router)
app.include_router(player_router)
app.include_router(player_stats)
app.include_router(clan_router)
app.include_router(admin_router)


def create_exception_handler(status_code: int, initial_detail: str) -> Callable:
    async def exception_handler(_: Request, exc: BaseCustomException):
        # Генерируем новое сообщение
        if isinstance(exc, BaseCustomException) and exc.message:
            message = exc.message
        else:
            message = initial_detail
        logger.exception(f"Ошибка {type(exc).__name__}: {exc}")

        # Логирование ошибки
        if isinstance(exc, NoUpdateClan) or isinstance(exc, NoUpdatePlayer):
            LoggerFactory.log(exc, level="CRITICAL")

        elif isinstance(exc, BaseCustomException):
            LoggerFactory.log(exc, level="ERROR")

        else:
            LoggerFactory.log(exc, level="CRITICAL")

        return JSONResponse(status_code=status_code, content={"detail": message})

    return exception_handler


def register_exception_handlers(app: FastAPI):
    for exc_class, (status_code, default_message) in EXCEPTION_HANDLERS.items():
        app.add_exception_handler(
            exc_class, create_exception_handler(status_code, default_message)
        )


register_exception_handlers(app)


@app.get("/")
async def root():
    return RedirectResponse("/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        access_log=False,  # Включает логи запросов uvicorn
    )
