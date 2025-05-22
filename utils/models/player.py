from datetime import datetime
from pydantic import BaseModel, Field
from decimal import Decimal

from utils.models.respnse_model import General, Region, RestUser
from utils.models.base_models import Session
from utils.models.tank import Tank, StatsTank, PlayerModel, Rating


class PlayerDetails(PlayerModel, Session):
    tanks: list[Tank]

    def __sub__(self, other) -> object:
        data = super().__sub__(other)
        data = data.model_dump()
        tanks = []
        other_tanks = {element.tank_id: element for element in other.tanks}
        self_tanks = {element.tank_id: element for element in self.tanks}
        length = max(other_tanks.keys(), self_tanks.keys())
        for key in length:
            res = self_tanks.get(
                key, Tank(tank_id=key, all=StatsTank())
            ) - other_tanks.get(key, Tank(tank_id=key, all=StatsTank()))
            if res:
                tanks.append(res)

        data["tanks"] = tanks

        return PlayerDetails(**data)

    def result(self, type="session"):
        model = super().result(type=type)
        match type:
            case "session":
                general = General(session=[tank.result() for tank in self.tanks])
            case "now":
                general = General(now=[tank.result() for tank in self.tanks])
            case "update":
                general = General(update=[tank.result() for tank in self.tanks])
        model.tanks = general
        return model


class UserDB(BaseModel, Session):
    region: str | None
    name: str | None
    player_id: int | None = None
    access_token: str | None = None
    acount: PlayerDetails | PlayerModel = None
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

    def __sub__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.model_copy(
            update={
                "acount": self.acount - other.acount,
                "timestamp": self.timestamp - other.timestamp,
            },
            deep=True,
        )

    def result(self, type="session") -> RestUser:
        model = self.acount.result(type=type)
        model.region = Region(self.region)
        model.time = self.timestamp
        return model


class RestPlayer(BaseModel):
    id: int
    name: str
    region: str
    private: dict | None = None
    general: dict | None = None
    time: int | datetime | str
    tanks: list[dict] | None = None

    def __sub__(self, other):
        if not isinstance(other, RestPlayer):
            return NotImplemented
        all_now = self.general["statistics"]["all"]
        all_old = other.general["statistics"]["all"]
        general = {
            k: float(Decimal(str(all_old.get(k, 0))) - Decimal(str(all_now.get(k, 0))))
            for k in all_now.keys()
        }
        tanks = []
        for n, o in zip(self.tanks, other.tanks):
            tank = {
                k: float(
                    Decimal(str(o["all"].get(k, 1))) - Decimal(str(n["all"].get(k, 1)))
                )
                for k in o["all"].keys()
            }

            tanks.append({"tank_id": o["tank_id"], "all": tank})
        return self.model_copy(
            update={"general": general, "tanks": tanks, "private": None}, deep=True
        )
