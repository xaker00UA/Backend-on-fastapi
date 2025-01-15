from pydantic import BaseModel, SerializeAsAny
from typing import Union


class BaseStats(BaseModel):
    battles: int = 0
    winrate: float = 0
    damage: float = 0
    accuracy: float = 0
    survival: float = 0
    avg_xp: float = 0
    wins_and_survived: float = 0
    murder_to_murder: float = 0
    damage_coefficient: float = 0

    def __sub__(self, other):
        if isinstance(other, BaseStats):
            return self.model_copy(
                update={
                    attr: round(getattr(self, attr) - getattr(other, attr), 2)
                    for attr in vars(self)
                    if getattr(self, attr) and getattr(other, attr)
                }
            )


class RestStatsTank(BaseStats):
    profit_coefficient: float = 0


class RestRating(BaseStats):
    score: int | None = None
    number: int | None = None


class RestStatistics(BaseModel):
    rating: RestRating | None = None
    all: RestStatsTank | None = None

    def __sub__(self, other):
        if isinstance(other, RestStatistics):
            all, rating = None, None
            if self.all and other.all:
                all = self.all - other.all
            if self.rating and other.all:
                rating = self.rating - other.rating
            return self.model_copy(update={"all": all, "rating": rating})
        return {"all": None, "rating": None}


class ItemTank(BaseModel):
    all: RestStatsTank | None = None
    name: str = "undefined"
    level: int | str = "undefined"
    last_battle_time: int = 0
    tank_id: int

    def __sub__(self, other):
        if isinstance(other, ItemTank) and self.tank_id == other.tank_id:
            return self.model_copy(
                update={
                    "all": self.all - other.all,
                }
            )


class General(BaseModel):
    update: RestStatistics | list[ItemTank] | None = None
    now: RestStatistics | list[ItemTank] | None = None
    session: RestStatistics | list[ItemTank] | None = None

    def __sub__(self, other):
        if isinstance(other, General):
            data = {}
            for field in ["update", "now", "session"]:
                self_field = getattr(self, field)

                other_field = getattr(other, field)

                if self_field is None and other_field is None:
                    continue

                if isinstance(self_field, RestStatistics):
                    data[field] = self_field - other_field
                elif isinstance(self_field, list) and isinstance(other_field, list):
                    # Если это списки, итерируем по меньшему из них с учетом совпадения id
                    updated_list = []
                    self_dict = {
                        item.tank_id: item for item in self_field
                    }  # Создаем словарь по id
                    other_dict = {
                        item.tank_id: item for item in other_field
                    }  # Создаем словарь по id

                    # Итерируем по каждому элементу из меньшего списка
                    for tank_id in min(self_dict, other_dict, key=len):
                        if tank_id in other_dict and tank_id in self_dict:
                            updated_item = self_dict[tank_id] - other_dict[tank_id]
                            updated_list.append(updated_item)

                    data[field] = updated_list

            return self.model_copy(update=data)


class RestPrivate(BaseModel):
    gold: int = 0
    free_xp: int = 0
    credits: int = 0
    is_premium: bool = False
    premium_expires_at: int = 0
    battle_life_time: int = 0

    def __sub__(self, other):
        if isinstance(other, RestPrivate):
            return self.model_copy(
                update={
                    attr: round(getattr(self, attr) - getattr(other, attr), 2)
                    for attr in vars(self)
                    if getattr(self, attr)
                    and getattr(other, attr)
                    and isinstance(getattr(self, attr), int)
                }
            )


class RestUser(BaseModel):
    id: int | None = None
    name: str | None = None
    region: str | None = None
    time: int | str | None = None
    private: RestPrivate | None = None
    general: General | None = None
    tanks: General | None = None

    def __sub__(self, other):
        if isinstance(other, RestUser):
            return self.model_copy(
                update={
                    "tanks": self.tanks - other.tanks,
                    "general": self.general - other.general,
                    "private": (
                        self.private - other.private
                        if self.private and other.private
                        else None
                    ),
                    "time": self.time - other.time,
                }
            )


class RestMember(BaseModel):
    id: int
    nickname: str
    general: RestStatistics | None = None
    last_battle_time: int | str


class RestClan(BaseModel):
    region: str
    name: str
    clan_id: int
    tag: str
    members_count: int
    members: list[RestMember]
    time: int | str | None
