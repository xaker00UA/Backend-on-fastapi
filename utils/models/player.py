from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel
from collections import Counter
from decimal import Decimal

from utils.error.exception import NoUpdatePlayer, NoUpdateTank, ValidError
from .base_models import Data_class, Session
from .tank import Tank, StatsTank, StatsPlayer, PlayerModel, Rating


class PlayerGeneral(PlayerModel):
    def result(self):
        return super().result()


class PlayerDetails(BaseModel, Session):
    general: PlayerGeneral | None = None
    tanks: list[Tank]

    def __sub__(self, other) -> object:
        if super().__sub__(other):
            if (self.general and other.general) is not None:
                general = self.general - other.general
            else:
                general = None
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
            return PlayerDetails(general=general, tanks=tanks)

    def result(self):
        data = None
        if self.general:
            data = self.general.result()
        res = [t.result() for t in self.tanks]
        return (
            {
                "time": data.pop("time"),
                "private": data.pop("private", None),
                "general": data,
                "tanks": res,
            }
            if data
            else {"tanks": res}
        )


class User(BaseModel):
    region: str | None
    name: str | None
    player_id: int = None
    access_token: str | None = None
    acount: PlayerDetails | PlayerGeneral = None

    class Config:
        extra = "ignore"

    def __sub__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.model_copy(update={"acount": self.acount - other.acount})


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
