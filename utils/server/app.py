from typing import Callable
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware


from fastapi.responses import JSONResponse
from .auth import router as auth_router
from .api_player import router as player_router, stats as player_stats
from .api_clan.api_clan import router as clan_router
from .admin.admin import router as admin_router
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ..interfase.player import PlayerSession
from ..interfase.clan import ClanInterface
from ..database.admin import initialize_db
from .middleware import ExceptionLoggingMiddleware
from ..error.exception import *
from ..settings.logger import LoggerFactory


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_db()
    scheduler = AsyncIOScheduler()
    trigger = CronTrigger(hour=12, minute=00, second=00)
    trigger_clan = CronTrigger(week=1, day_of_week="mon", hour=12, minute=00)
    scheduler.add_job(PlayerSession.update_db, trigger=trigger)
    scheduler.add_job(ClanInterface.update_db, trigger=trigger_clan)
    scheduler.add_job(PlayerSession.update_player_token, trigger=trigger_clan)
    LoggerFactory.info("Start scheduler job")
    scheduler.start()
    yield
    LoggerFactory.info(
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
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
]


app = FastAPI(title="Authentication", lifespan=lifespan, middleware=mid)
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

        # Логирование ошибки
        if isinstance(exc, Exception):
            LoggerFactory.critical(exc, exc_info=True)
        else:
            LoggerFactory.error(exc, exc_info=True)

        return JSONResponse(status_code=status_code, content={"detail": message})

    return exception_handler


def register_exception_handlers(app: FastAPI):
    for exc_class, (status_code, default_message) in EXCEPTION_HANDLERS.items():
        app.add_exception_handler(
            exc_class, create_exception_handler(status_code, default_message)
        )


register_exception_handlers(app)


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
        access_log=False,  # Включает логи запросов uvicorn
    )
