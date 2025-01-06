class BaseCustomException(Exception):
    pass


class ValidError(BaseCustomException):
    pass


class PlayerNotFound(BaseCustomException):
    pass


class ClanNotFound(BaseCustomException):
    def __init__(self, clan_name: str):
        # Формируем сообщение об ошибке, включая имя клана
        self.message = f"Клан '{clan_name}' не найден"
        super().__init__(self.message)


class RequestError(BaseCustomException):
    pass


class NoUpdateTank(BaseCustomException):
    pass


class NoUpdatePlayer(BaseCustomException):
    pass


class NoUpdateClan(BaseCustomException):
    pass


class NotFoundPlayerDB(BaseCustomException):
    def __init__(self, **kwargs):
        args = [f"{key}={value}" for key, value in kwargs.items() if value]

        # Формируем основное сообщение
        message = (
            f"Игрок не найден. Со следующими аргументами {', '.join(args)}"
            if args
            else "Игрок не найден. Аргументов нет"
        )

        # Устанавливаем сообщение об ошибке
        self.message = message
        super().__init__(self.message)


class NotFoundClanDB(BaseCustomException):
    def __init__(self, clan_name: str):
        # Формируем сообщение об ошибке, включая имя клана
        self.message = f"Клан '{clan_name}' только начали отслеживать"
        super().__init__(self.message)
