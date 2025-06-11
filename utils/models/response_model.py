from enum import Enum
from typing import Callable
from pydantic import BaseModel, PrivateAttr, model_validator, Field


class Region(str, Enum):
    eu = "eu"
    asia = "asia"
    com = "com"
    na = "na"


class Medal(BaseModel):
    name: str
    image: str = "undefined"
    count: int

    def __sub__(self, other):
        if not isinstance(other, Medal):
            return NotImplemented
        count = self.count - other.count
        return self.model_copy(update={"count": count}, deep=True)


class Medals(BaseModel):
    medals: list[Medal] = []

    def __sub__(self, other):
        if not isinstance(other, Medals):
            return NotImplemented
        medals = []
        other_medals = {element.name: element for element in other.medals}
        for medal in self.medals:
            if medal.name in other_medals:
                medals.append(medal - other_medals[medal.name])
            else:
                medals.append(medal)
        return self.model_copy(update={"medals": medals}, deep=True)


class BaseStats(BaseModel):
    battles: int = Field(default=0)
    winrate: float = Field(default=0)
    damage: float = Field(default=0)
    accuracy: float = Field(default=0)
    survival: float = Field(default=0)
    avg_xp: float = Field(default=0)
    wins_and_survived: float = Field(default=0)
    murder_to_murder: float = Field(default=0)
    damage_coefficient: float = Field(default=0)

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
    profit_coefficient: float = Field(default=0)


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


class Images(BaseModel):
    preview: str | None = None
    normal: str | None = None


class ItemTank(BaseModel):
    all: RestStatsTank | None = None
    nation: str = "undefined"
    images: Images = Images()
    name: str = "undefined"
    level: int | str = "undefined"
    is_premium: bool = False
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


class GeneralTanks(General):
    update: list[ItemTank] | None = None
    now: list[ItemTank] | None = None
    session: list[ItemTank] | None = None


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


class RestUserDB(BaseModel):
    region: Region
    name: str
    player_id: int


class RestUser(RestUserDB):
    time: int = 1
    private: RestPrivate | None = None
    general: General
    tanks: GeneralTanks | None = None
    medals: Medals = Medals()

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
    general: BaseStats = BaseStats()
    time: int | str | None


class ErrorResponse(BaseModel):
    detail: str


class Parameter(str, Enum):
    battles = "battles"
    wins = "wins"
    damage = "damage"


class LoginForm(BaseModel):
    username: str
    password: str


class Commands(Enum):
    reset = "!reset_user"
    reset_clan = "!reset_clan"
    delete = "!delete_user"
    delete_clan = "!delete_clan"
    update_player_db = "!update_player_db"
    update_clan_db = "!update_clan_db"


class Command(BaseModel):
    command: Commands
    region: Region | None = None
    arguments: str = ""

    _task: Callable | None = PrivateAttr(default=None)

    async def run(self):
        if self._task:
            return await self._task

    @model_validator(mode="after")
    def convector(self):
        self.region = (
            self.region.value if isinstance(self.region, Region) else self.region
        )
        return self

    @model_validator(mode="after")
    def valid(self):
        from utils.interfase.clan import ClanInterface
        from utils.interfase.player import PlayerSession

        if self.command == Commands.reset:
            self._task = PlayerSession(name=self.arguments, reg=self.region).reset()
        elif self.command == Commands.reset_clan:
            self._task = ClanInterface(region=self.region, tag=self.arguments).reset()
        elif self.command == Commands.update_player_db:
            self._task = PlayerSession.update_db()
        elif self.command == Commands.update_clan_db:
            self._task = ClanInterface.update_db()
        elif self.command == Commands.delete:
            # Замените на нужное действие
            self._task = ...
        elif self.command == Commands.delete_clan:
            # Замените на нужное действие
            self._task = ...
        else:
            raise TypeError("Invalid command")
        return self


class AuthLogin(BaseModel):
    success: str = "ok"
    url: str


class AuthVerify(BaseModel):
    isAuthenticated: bool


class TopPlayer(RestUserDB):
    parameter: Parameter
    value: float | int
