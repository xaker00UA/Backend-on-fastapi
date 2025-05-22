from pydantic import BaseModel, computed_field
from typing import Optional
from utils.models.base_models import Session
from utils.models.configmodel import StrMixin
from utils.models.respnse_model import (
    General,
    ItemTank,
    Region,
    RestPrivate,
    RestRating,
    RestStatistics,
    RestStatsTank,
    RestUser,
)


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

    @computed_field(return_type=float)
    @property
    def damage(self):
        return round(self.damage_dealt / self.battles, 2) if self.battles != 0 else 0

    @computed_field(return_type=float)
    @property
    def winrate(self):
        return round(self.wins / self.battles * 100, 2) if self.battles != 0 else 0

    @computed_field(return_type=float)
    @property
    def accuracy(self):
        return round(self.hits / self.shots * 100, 2) if self.shots != 0 else 0

    @computed_field(return_type=float)
    @property
    def survival(self):
        return (
            round(self.survived_battles / self.battles * 100, 2)
            if self.battles != 0
            else 0
        )

    @computed_field(return_type=float)
    @property
    def avg_xp(self):
        return round(self.xp / self.battles, 2) if self.battles != 0 else 0

    @computed_field(return_type=float)
    @property
    def wins_and_survived(self):
        return (
            round(self.win_and_survived / self.battles * 100, 2)
            if self.battles != 0
            else 0
        )

    @computed_field(return_type=float)
    @property
    def murder_to_murder(self):
        return round(self.frags / self.battles, 2) if self.battles != 0 else 0

    @computed_field(return_type=float)
    @property
    def damage_coefficient(self):
        return (
            round(self.damage_dealt / self.damage_received, 2)
            if self.damage_received != 0
            else 0
        )

    def __sub__(self, other):
        if super().__sub__(other):
            if self.__ne__(other):
                res = {}
                for attrs in vars(self):
                    res[attrs] = abs(getattr(self, attrs) - getattr(other, attrs))
                res = self.model_copy(update=res)
                if res.battles == 0:
                    return None
                return res
        else:
            return NotImplemented

    def result(self):
        return RestStatsTank(**self.model_dump())


# Модель танка
class Tank(BaseModel, Session):
    all: StatsTank
    last_battle_time: int = 0
    battle_life_time: int = 0
    in_garage: Optional[bool] = None
    tank_id: int = 0

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
        data = self.model_dump()
        data["all"] = self.all.result()
        return ItemTank(**data)


class Private(BaseModel, Session):
    gold: int = 0
    ban_info: Optional[str] = None
    free_xp: int = 0
    ban_time: Optional[int] = None
    is_premium: bool
    credits: int = 0
    premium_expires_at: int = 0
    battle_life_time: int = 0

    def __sub__(self, other: object):
        if isinstance(other, self.__class__):
            if self.__eq__(other):
                return None
            res = {}
            for field, value in vars(self).items():
                if field not in ["ban_info", "ban_time", "is_premium"]:
                    res[field] = value - getattr(other, field)
            return self.model_copy(update=res)

    def result(self):
        return RestPrivate(**self.model_dump())


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

    def __sub__(self, other):
        if super().__sub__(other):
            if self.__eq__(other):
                return None
            result = {}
            for field, value in vars(self).items():
                if not isinstance(value, bool) and isinstance(value, (int, float)):
                    result[field] = abs(getattr(self, field) - getattr(other, field))
            if result["battles"] == 0:
                return None
            return self.model_copy(update=result)
        else:
            raise TypeError("Ожидается объект класса %s", self.__class__.__name__)

    def result(self):
        res = StatsTank(**self.model_dump()).result()
        return RestRating(score=self.score, number=self.number, **res.model_dump())


class Statistics(BaseModel, Session):
    rating: Rating | None
    all: StatsTank | None

    def __sub__(self, other):
        if isinstance(other, self.__class__):
            all = self.all - other.all
            rating = self.rating - other.rating
            return self.model_copy(update={"all": all, "rating": rating})
        else:
            return NotImplemented

    def result(self):
        data, all = None, None
        if self.rating:
            data = self.rating.result()
        if self.all:
            all = self.all.result()
        return RestStatistics(all=all, rating=data)


# Общая модель игрока
class PlayerModel(BaseModel, Session, StrMixin):
    nickname: str
    account_id: int = 0
    created_at: int = 0
    updated_at: int = 0
    private: Private | None
    statistics: Statistics
    last_battle_time: int = 0

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

    def result(self, type="session") -> RestUser:
        private = self.private.result() if self.private else None
        match type:
            case "session":
                general = General(session=self.statistics.result())
            case "now":
                general = General(now=self.statistics.result())
            case "update":
                general = General(update=self.statistics.result())

        return RestUser(
            region=Region("eu"),
            player_id=self.account_id,
            name=self.nickname,
            private=private,
            general=general,
        )
