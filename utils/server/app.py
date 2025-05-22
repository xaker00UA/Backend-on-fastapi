import traceback
from typing import Callable
import warnings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware import Middleware


from fastapi.responses import JSONResponse

from utils.models.respnse_model import ErrorResponse
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
from ..api.wotb import APIServer

scheduler = AsyncIOScheduler()
scheduler.configure({"coalesce": True, "misfire_grace_time": 60})


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    initialize_db()
    server = APIServer()
    await server.init_session()
    trigger = CronTrigger(hour=12, minute=00, second=00)
    trigger_clan = CronTrigger(day_of_week="mon", hour=12, minute=00)
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
    LoggerFactory.info("Start scheduler job")
    scheduler.start()
    yield
    await server.close()
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
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
]


app = FastAPI(
    title="Authentication",
    lifespan=lifespan,
    servers=[{"url": "http://localhost:8000"}, {"url": "http://localhost:3000"}],
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

        # Логирование ошибки
        if isinstance(exc, NoUpdateClan) or (exc, NoUpdatePlayer):
            LoggerFactory.critical(exc, exc_info=True)
        elif isinstance(exc, BaseCustomException):
            LoggerFactory.error(exc, exc_info=True)
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
    jobs = scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": (
                job.next_run_time.isoformat() if job.next_run_time else None
            ),
            "trigger": str(job.trigger),
        }
        for job in jobs
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        access_log=False,  # Включает логи запросов uvicorn
    )
