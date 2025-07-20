import sys
import json
from pathlib import Path
import traceback
from typing import Literal

from .config import Config
from loguru import logger

settings = Config()


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class LoggerFactory:
    names = ["root", "http", "api"]

    @staticmethod
    def last_stack_lines(limit=5):
        stack = traceback.format_stack(limit=limit)
        return "".join(stack)

    @staticmethod
    def setup():
        logger.remove(0)  # Удалить стандартный хендлер
        logger.level("INFO", color="<green>", icon="✅")
        # Консольный лог
        logger.add(
            sys.stdout,
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> |<level> {level.icon:^3} </level> | <level>{level:^8}</level> |   <yellow>{message}</yellow>",
            enqueue=True,
            backtrace=False,
            diagnose=False,
        )

        # INFO лог — хранится 14 дней
        logger.add(
            LOG_DIR / "info.log",
            level="INFO",
            filter=lambda r: r["level"].name == "INFO"
            and r["extra"].get("channel") == "root",
            retention="14 days",
            rotation="20 MB",
            format=LoggerFactory._json_formatter,
            enqueue=True,
        )

        # DEBUG лог — хранится 2 дня
        logger.add(
            LOG_DIR / "debug.log",
            level="DEBUG",
            retention="2 days",
            filter=lambda r: r["extra"].get("channel") in LoggerFactory.names,
            rotation="10 MB",
            format=LoggerFactory._json_formatter,
            enqueue=True,
        )

        # WARNING и выше
        logger.add(
            LOG_DIR / "error.log",
            level="ERROR",
            retention="10 days",
            rotation="10 MB",
            format=LoggerFactory._critical_formatter,
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )

        # CRITICAL ошибки + стек (5 строк)
        logger.add(
            LOG_DIR / "critical.log",
            level="CRITICAL",
            retention="14 days",
            rotation="5 MB",
            serialize=True,  # format=LoggerFactory._critical_formatter,
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )
        # API внешний
        logger.add(
            LOG_DIR / "api.log",
            level="DEBUG",
            filter=lambda record: record["extra"].get("channel") == "api",
            retention="2 days",
            rotation="10 MB",
            format=LoggerFactory._json_formatter,
            enqueue=True,
        )
        # http
        logger.add(
            LOG_DIR / "http.log",
            level="DEBUG",
            filter=lambda record: record["extra"].get("channel") == "http",
            retention="2 days",
            rotation="10 MB",
            format=LoggerFactory._json_formatter,
            enqueue=True,
        )

    @staticmethod
    def _json_formatter(record):
        """Кастомный сериализатор для логов в JSON"""
        log_entry = {
            "time": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "name": record["name"],
            "function": record["function"],
            "line": record["line"],
            "extra": record.get("extra", {}),
        }

        string = json.dumps(log_entry, ensure_ascii=False) + "\n"
        string = string.replace("{", "{{").replace("}", "}}")

        return string

    @staticmethod
    def _critical_formatter(record):

        string = (
            json.dumps(
                {
                    "time": record["time"].isoformat(),
                    "level": record["level"].name,
                    "message": record["message"],
                    "name": record["name"],
                    "function": record["function"],
                    "line": record["line"],
                    "short_trace": record.get("RecordException"),
                    "extra": record.get("extra", {}),
                },
                ensure_ascii=False,
            )
            + "\n"
        )

        string = string.replace("{", "{{").replace("}", "}}")
        return string

    @staticmethod
    def log(
        message: str,
        channel: Literal["root", "http", "api"] = "root",
        level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
        **extra,
    ):
        logger.bind(channel=channel, **extra).log(level, message)

    @staticmethod
    def test_exp(str):
        logger.exception(str)

    @staticmethod
    def head_log(limit=100):
        with open(LOG_DIR / "debug.log", "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
            lines = [line.strip() for line in lines]
            lines = [json.loads(line) for line in lines]
        return lines


log = LoggerFactory.setup()
