from enum import Enum
from pydantic import BaseModel, model_validator


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
    region: "Region" = "Region.eu"
    name: str
    player_id: int


class RestUser(RestUserDB):
    time: int = 1
    private: RestPrivate | None = None
    general: General
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
    general: BaseStats = BaseStats()
    time: int | str | None


class ErrorResponse(BaseModel):
    detail: str


class Region(str, Enum):
    eu = "eu"
    asia = "asia"
    com = "com"
    na = "na"


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

    def run(self):
        if hasattr(self, "task"):
            return self.task

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
            self.task = PlayerSession(name=self.arguments, reg=self.region).reset()
        elif self.command == Commands.reset_clan:
            self.task = ClanInterface(region=self.region, tag=self.arguments).reset()
        elif self.command == Commands.update_player_db:
            self.task = PlayerSession.update_db()
        elif self.command == Commands.update_clan_db:
            self.task = ClanInterface.update_db()
        elif self.command == Commands.delete:
            # Замените на нужное действие
            self.task = ...
        elif self.command == Commands.delete_clan:
            # Замените на нужное действие
            self.task = ...
        else:
            raise TypeError("Invalid command")
        return self


class AuthLogin(BaseModel):
    success: str = "ok"
    url: str


class AuthVerify(BaseModel):
    isAuthenticated: bool = False
