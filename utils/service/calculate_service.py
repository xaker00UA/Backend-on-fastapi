from ..models.player import UserDB
from pydantic import BaseModel
from ..models.base_models import Session
from ..models.clan import ClanDB
from ..models.tank import (
    StatsTank,
    Private,
    Rating,
    StatsPlayer,
    Statistics,
    PlayerModel,
    Tank,
)
from ..models.respnse_model import (
    BaseStats,
    General,
    ItemTank,
    RestPrivate,
    RestRating,
    RestStatistics,
    RestStatsTank,
    RestUser,
    RestClan,
    RestMember,
)


class CallService:
    @staticmethod
    def calculate_difference(
        old_model: Session, now_model: Session, result_model: BaseModel
    ) -> BaseModel:
        """
        Вычисляет разницу между двумя моделями и возвращает новую модель на основе результата.

        :param old_model: Старая версия модели.
        :param now_model: Текущая версия модели.
        :param result_model: Класс модели результата, например, RestStatsTank.
        :return: Экземпляр result_model с рассчитанными данными.
        """
        # Вычисляем разницу между моделями
        substr_model = now_model - old_model
        if substr_model is None:
            return result_model()  # Пустой результат, если разница отсутствует

        # Генерируем данные из результата
        data = substr_model.result()
        return result_model(**data)

    @staticmethod
    def get_base_stats(old_model: StatsTank, now_model: StatsTank) -> BaseStats:
        return CallService.calculate_difference(
            old_model=old_model, now_model=now_model, result_model=BaseStats
        )

    @staticmethod
    def get_stats_tank(old_model: StatsTank, now_model: StatsTank) -> RestStatsTank:
        return CallService.calculate_difference(
            old_model=old_model, now_model=now_model, result_model=RestStatsTank
        )

    @staticmethod
    def get_stats_rating(old_model: Rating, now_model: Rating) -> RestRating:
        return CallService.calculate_difference(
            old_model=old_model, now_model=now_model, result_model=RestRating
        )

    @staticmethod
    def get_statistics(old_model: Statistics, now_model: Statistics) -> RestStatistics:
        return CallService.calculate_difference(
            old_model=old_model, now_model=now_model, result_model=RestStatistics
        )

    @staticmethod
    def get_item_tank(old_model: Tank, now_model: Tank) -> ItemTank:
        return CallService.calculate_difference(
            old_model=old_model, now_model=now_model, result_model=ItemTank
        )

    @staticmethod
    def get_general(old_model: Session, now_model: Session) -> General:
        return CallService.calculate_difference(
            old_model=old_model, now_model=now_model, result_model=General
        )

    @staticmethod
    def get_tank_general(old_model: Session, now_model: Session) -> General:
        return CallService.calculate_difference(
            old_model=old_model, now_model=now_model, result_model=General
        )

    @staticmethod
    def get_private(old_model: Private, now_model: Private) -> RestPrivate:
        return CallService.calculate_difference(
            old_model=old_model, now_model=now_model, result_model=RestPrivate
        )

    @staticmethod
    def get_achievements(old_model: Session, now_model: Session):
        pass

    @staticmethod
    def get_clan_members(old_model: Session, now_model: Session) -> RestMember:
        return CallService.calculate_difference(
            old_model=old_model, now_model=now_model, result_model=RestMember
        )

    @staticmethod
    def get_rest_user(old_model: UserDB, now_model: UserDB) -> RestUser:
        old_ac = old_model.acount
        now_ac = now_model.acount
        return CallService.calculate_difference(
            old_model=old_model, now_model=now_model, result_model=RestUser
        )

    @staticmethod
    def get_rest_clan(old_model: Session, now_model: Session) -> RestClan:
        return CallService.calculate_difference(
            old_model=old_model, now_model=now_model, result_model=RestClan
        )
