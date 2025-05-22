from datetime import datetime
import inspect
import logging
from logging.handlers import RotatingFileHandler
import sys
import json
import traceback
from pathlib import Path
from .config import Singleton, Config


settings = Config()

logging.getLogger()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.now().replace(microsecond=0).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "duration"):
            log_record["duration"] = round(record.duration, 4)
        if hasattr(record, "method"):
            log_record["method"] = record.method

        # log_record["file"] = record.caller_file
        # log_record["line"] = record.caller_line
        # log_record["func"] = record.caller_func

        return json.dumps(log_record, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    def format(self, record):

        timestamp = datetime.now().replace(microsecond=0).isoformat()
        level = record.levelname
        name = record.name
        message = record.getMessage()

        return f"{timestamp}| {level} | {name} | {message} |"


class LoggerFactory(Singleton):
    name = "root"

    @classmethod
    def _get_logger(
        cls, name: str | None = None, level=logging.DEBUG
    ) -> logging.Logger:
        logger_name = name or cls.name
        logger = logging.getLogger(logger_name)
        logger.propagate = False
        logger.setLevel(level)
        if logger.hasHandlers():
            return logger

            # --- Общий для всех: консоль ---
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ConsoleFormatter())
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

        # --- Для http логгера ---
        if logger_name == "http":
            http_handler = RotatingFileHandler(
                LOG_DIR / "http_requests.log",
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            http_handler.setFormatter(JsonFormatter())
            http_handler.setLevel(logging.DEBUG)
            logger.addHandler(http_handler)

        # --- Для API логгера ---
        elif logger_name == "api":
            api_handler = RotatingFileHandler(
                LOG_DIR / "api.log",
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            api_handler.setFormatter(JsonFormatter())
            api_handler.setLevel(logging.DEBUG)
            logger.addHandler(api_handler)

        # --- Для root логгера (основное приложение) ---
        elif logger_name == "root":
            app_handler = RotatingFileHandler(
                LOG_DIR / "app.log",
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            app_handler.setFormatter(JsonFormatter())
            app_handler.setLevel(logging.INFO)
            logger.addHandler(app_handler)

            debug_handler = RotatingFileHandler(
                LOG_DIR / "debug.log",
                maxBytes=10 * 1024 * 1024,
                backupCount=1,
                encoding="utf-8",
            )
            debug_handler.setFormatter(JsonFormatter())
            debug_handler.setLevel(logging.DEBUG)
            logger.addHandler(debug_handler)

            error_handler = RotatingFileHandler(
                LOG_DIR / "error.log",
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            error_handler.setFormatter(JsonFormatter())
            error_handler.setLevel(logging.ERROR)
            logger.addHandler(error_handler)

        libs_to_silence = ["pymongo", "apscheduler", "scheduler"]

        for name in logging.root.manager.loggerDict:
            if any(name.startswith(lib) for lib in libs_to_silence):
                logging.getLogger(name).setLevel(logging.CRITICAL + 1)
                logging.getLogger(name).propagate = False

        return logger

    @classmethod
    def _get_calling_context(cls):
        # Извлекаем информацию о месте вызова
        stack = inspect.stack()
        caller = stack[2]  # Стек вызывает второй элемент
        filename = Path(caller.filename).name
        line_number = caller.lineno
        func_name = caller.function

        return {
            "caller_file": filename,
            "caller_line": line_number,
            "caller_func": func_name,
        }

    @classmethod
    def debug(cls, message: str, name: str | None = None, extra: dict | None = None):
        logger = cls._get_logger(name, logging.DEBUG)
        context = cls._get_calling_context()
        logger.debug(message, extra={**context, **(extra or {})})

    @classmethod
    def info(cls, message: str, name: str | None = None, extra: dict | None = None):
        logger = cls._get_logger(name, logging.INFO)
        context = cls._get_calling_context()
        logger.info(message, extra={**context, **(extra or {})})

    @classmethod
    def warn(cls, message: str, name: str | None = None, extra: dict | None = None):
        logger = cls._get_logger(name, logging.WARNING)
        context = cls._get_calling_context()
        logger.warning(message, extra={**context, **(extra or {})})

    @classmethod
    def error(
        cls,
        message: str,
        name: str | None = None,
        exc_info: bool = True,
        extra: dict | None = None,
    ):
        logger = cls._get_logger(name, logging.ERROR)
        context = cls._get_calling_context()
        logger.error(message, exc_info=exc_info, extra={**context, **(extra or {})})

    @classmethod
    def critical(
        cls,
        message: str,
        name: str | None = None,
        exc_info: bool = True,
        extra: dict | None = None,
    ):
        logger = cls._get_logger(name, logging.CRITICAL)
        context = cls._get_calling_context()
        logger.critical(message, exc_info=exc_info, extra={**context, **(extra or {})})
