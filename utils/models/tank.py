from abc import ABCMeta
from dataclasses import dataclass, field
import time
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, Dict
from utils.error.exception import NoUpdateTank
from .base_models import Data_class, Session
from .configmodel import StrMixin


# Модель статистики игрового танка и игрока
class StatsTank(BaseModel, Session):
    spotted: int = 0
    hits: int = 0
    frags: int = 0
    max_xp: int = 0
    wins: int = 0
    losses: int = 0
    capture_points: int = 0
    battles: int = 0
    damage_dealt: int = 0
    damage_received: int = 0
    max_frags: int = 0
    shots: int = 0
    frags8p: int = 0
    xp: int = 0
    win_and_survived: int = 0
    survived_battles: int = 0
    dropped_capture_points: int = 0

    class Config:
        extra = "ignore"

    def __eq__(self, other: object) -> bool:
        if isinstance(self, other.__class__):
            return all(getattr(self, k) == getattr(other, k) for k in self.__dict__)
        return False

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __sub__(self, other):
        if super().__sub__(other):
            if self.__ne__(other):
                res = {}
                for attrs in vars(self):
                    res[attrs] = abs(getattr(self, attrs) - getattr(other, attrs))
                return self.model_copy(update=res)
        else:
            return NotImplemented

    def result(self):
        if self.battles != 0:
            battles = self.battles
            wins = round(self.wins / self.battles * 100, 2)
            damage = round(self.damage_dealt / self.battles, 2)
            accuracy = round(self.hits / self.shots * 100, 2) if self.shots != 0 else 0
            survived_battles = round(self.survived_battles / self.battles * 100, 2)
            xp = round(self.xp / self.battles, 2)
            win_and_survived = round(self.win_and_survived / self.battles * 100, 2)
            frags = round(self.frags / self.battles, 2)
            kpd = (
                round(self.damage_dealt / self.damage_received, 2)
                if self.damage_received != 0
                else 0
            )
        else:
            (
                battles,
                wins,
                damage,
                accuracy,
                survived_battles,
                xp,
                win_and_survived,
                frags,
                kpd,
            ) = (0, 0, 0, 0, 0, 0, 0, 0, 0)
        return {
            "Бои": battles,
            "Победы": wins,
            "Урон": damage,
            "Точность": accuracy,
            "Выживаемость": survived_battles,
            "Опыт за бой": xp,
            "Победил и выжил": win_and_survived,
            "Килы к убийств": frags,
            "КПД": kpd,
        }


# Модель дополнительная модель игрока
class StatsPlayer(StatsTank):
    max_frags_tank_id: int = 0
    max_xp_tank_id: int = 0

    # TODO: Update __sub__()
    class Config:
        extra = "ignore"


# Модель танка
class Tank(BaseModel, Session):
    all: StatsTank
    last_battle_time: int = 0
    account_id: int = 0
    in_garage_updated: Optional[int] = None
    frags: Optional[Dict[str, int]] = None
    mark_of_mastery: int = 0
    battle_life_time: int = 0
    in_garage: Optional[bool] = None
    tank_id: int = 0

    class Config:
        extra = "ignore"

    def __sub__(self, other: object):
        if super().__sub__(other):
            all = self.all - other.all
            if not all:
                return None
            last_battle_time = max(self.last_battle_time, other.last_battle_time)
            battle_life_time = max(self.battle_life_time, other.battle_life_time)
            return self.model_copy(
                update={
                    "all": all,
                    "battle_life_time": battle_life_time,
                    "last_battle_time": last_battle_time,
                }
            )
        else:
            return NotImplemented

    def result(self):
        res = {}
        res["all"] = self.all.result()
        res["tank_id"] = self.tank_id
        res["last_battle_time"] = time.ctime(self.last_battle_time)
        res["battle_life_time"] = get_time_str(self.battle_life_time)

        return res


class Private(BaseModel):
    gold: int = 0
    ban_info: Optional[str] = None
    free_xp: int = 0
    ban_time: Optional[int] = None
    is_premium: bool
    credits: int = 0
    premium_expires_at: int = 0
    battle_life_time: int = 0

    class Config:
        extra = "ignore"

    def __eq__(self, value: object) -> bool:
        if isinstance(value, self.__class__):
            return all(getattr(self, k) == getattr(value, k) for k in self.__dict__)
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __sub__(self, other: object):
        if isinstance(other, self.__class__):
            if self.__eq__(other):
                return None
            res = {}
            for field, value in vars(self).items():
                if field not in ["ban_info", "ban_time", "is_premium"]:
                    res[field] = abs(value - getattr(other, field))
            return self.model_copy(update=res)


# Модель рейтинга
class Rating(BaseModel, Session):
    spotted: int = 0
    calibration_battles_left: int = 0
    hits: int = 0
    frags: int = 0
    recalibration_start_time: int = 0
    mm_rating: float = 0
    wins: int = 0
    losses: int = 0
    is_recalibration: bool = False
    capture_points: int = 0
    battles: int = 0
    current_season: int = 0
    damage_dealt: int = 0
    damage_received: int = 0
    shots: int = 0
    frags8p: int = 0
    xp: int = 0
    win_and_survived: int = 0
    survived_battles: int = 0
    dropped_capture_points: int = 0
    score: int | None = None
    number: int | None = None

    def __eq__(self, value: object) -> bool:
        if isinstance(value, self.__class__):
            return all(getattr(self, k) == getattr(value, k) for k in self.__dict__)
        return False

    def __ne__(self, value: object) -> bool:
        return not self.__eq__(value)

    class Config:
        extra = "ignore"

    def __sub__(self, other):
        if super().__sub__(other):
            if self.__eq__(other):
                return None
            result = {}
            for field, value in vars(self).items():
                if isinstance(value, (int, float)):
                    result[field] = abs(getattr(self, field) - getattr(other, field))
            return self.model_copy(update=result)
        else:
            raise TypeError("Ожидается объект класса %s", self.__class__.__name__)

    def result(self):
        res = StatsPlayer(**self.__dict__).result()
        res["number"] = self.number
        res["score"] = self.score

        return res


class Statistics(BaseModel):
    rating: Optional[Rating] = None
    all: Optional[StatsPlayer] = None

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            all = self.all - other.all
            rating = self.rating - other.rating
            return self.model_copy(update={"all": all, "rating": rating})
        else:
            return NotImplemented

    def result(self):
        res = {}
        res["rating"] = self.rating.result() if self.rating else None
        res["all"] = self.all.result() if self.all else None
        return res

    class Config:
        extra = "ignore"


# Общая модель игрока
class PlayerModel(BaseModel, Session, StrMixin):
    account_id: int = 0
    created_at: int = 0
    updated_at: int = 0
    private: Private | None
    statistics: Statistics
    last_battle_time: int = 0
    nickname: str
    # OPTIMIZE: private.__sub__()

    def __sub__(self, other):
        if super().__sub__(other):
            update = abs(self.last_battle_time - other.last_battle_time)
            last_battle_time = max(self.last_battle_time, other.last_battle_time)
            statistics = self.statistics - other.statistics
            private = (
                self.private - other.private if self.private and other.private else None
            )
            return self.model_copy(
                update={
                    "updated_at": update,
                    "statistics": statistics,
                    "private": private,
                    "last_battle_time": last_battle_time,
                }
            )
        return NotImplemented

    def result(self):
        res = {}
        res["statistics"] = self.statistics.result()
        res["private"] = self.private.model_dump() if self.private else None
        res["last_battle_time"] = self.last_battle_time

        return res

    class Config:
        extra = "ignore"


def get_time_str(int):
    time_delta = timedelta(seconds=int)

    # Вывод дней, часов, минут и секунд
    days = time_delta.days
    hours, remainder = divmod(time_delta.seconds, 3600)  # Остаток после деления на часы
    minutes, seconds = divmod(remainder, 60)  # Остаток после деления на минуты

    return f"{days} дней, {hours} часов, {minutes} минут, {seconds} секунд."
