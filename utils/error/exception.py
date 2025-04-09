class BaseCustomException(Exception):
    def __init__(self, message: str = None, *args, **kwargs):
        # Собираем аргументы в строку, если они есть
        args = [f"{key}={value}" for key, value in kwargs.items() if value]

        # Формируем основное сообщение
        if args:
            message = (
                f"{message} с аргументами {', '.join(args)}"
                if message
                else f"Ошибка с аргументами {', '.join(args)}"
            )
        elif not message:
            message = "Произошла ошибка"

        self.message = message
        super().__init__(self.message)


class ValidError(BaseCustomException):
    pass


class PlayerNotFound(BaseCustomException):
    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message=message, **kwargs)
        else:
            super().__init__(message="Игрок не найден", **kwargs)


class ClanNotFound(BaseCustomException):
    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message=message, **kwargs)
        else:
            super().__init__(message="Клан не найден", **kwargs)


class RequestError(BaseCustomException):
    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message=message, **kwargs)
        else:
            super().__init__(message="Ошибка запроса", **kwargs)


class InvalidAccessToken(RequestError):
    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message=message, **kwargs)
        else:
            super().__init__(message="Не валидный токен игрока", **kwargs)


class InvalidApplicationId(RequestError):
    pass


class InvalidIpAddress(RequestError):
    pass


class RequestLimitExceeded(RequestError):
    pass


class ApplicationIsBlocked(RequestError):
    pass


class NoUpdateTank(BaseCustomException):
    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message=message, **kwargs)
        else:
            super().__init__(message="Не удалось обновить танк", **kwargs)


class NoUpdatePlayer(BaseCustomException):
    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message=message, **kwargs)
        else:
            super().__init__(message="Не удалось обновить игрока", **kwargs)


class NoUpdateClan(BaseCustomException):
    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message=message, **kwargs)
        else:
            super().__init__(message="Не удалось обновить клан", **kwargs)


class NotFoundPlayerDB(BaseCustomException):
    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message=message, **kwargs)
        else:
            super().__init__(message="Игрок не отслеживается", **kwargs)


class NotFoundPeriod(BaseCustomException):
    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message=message, **kwargs)
        else:
            super().__init__(message="Игрок не отслеживаеться так долго", **kwargs)


class NotFoundClanDB(BaseCustomException):
    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message=message, **kwargs)
        else:
            super().__init__(message="Клан не отслеживается", **kwargs)


class InvalidAdminToken(BaseCustomException):
    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message=message, **kwargs)
        else:
            super().__init__(message="Не валидный токен админа", **kwargs)


class ServerIsTemporarilyUnavailable(BaseCustomException):
    def __init__(self, message=None, **kwargs):
        if message:
            super().__init__(message=message, **kwargs)
        else:
            super().__init__(message="API временно не доступно", **kwargs)


EXCEPTION_HANDLERS = {
    NotFoundPlayerDB: (404, "Игрок не отслеживаеться"),
    InvalidAdminToken: (401, "Неверный токен админа"),
    InvalidAccessToken: (401, "Неверный токен пользователся"),
    NotFoundClanDB: (404, "Клан не отслеживаеться"),
    NotFoundPeriod: (400, "Игрок не отслеживаеться так долго"),
    ClanNotFound: (404, "Клан не найден"),
    PlayerNotFound: (404, "Игрок не найден"),
    ServerIsTemporarilyUnavailable: (504, "Сервер с данными временно не доступен"),
    RequestError: (400, "Не обработанная ошибка внешнего запроса"),
    ValidError: (422, "Не валидные данные"),
    Exception: (500, "Internal Server Error"),
    # Добавляй сколько нужно
}
