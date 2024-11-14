from datetime import datetime
from dataclasses import dataclass, field


from .tank import Tank
from .player import PlayerModel
from .base_models import Data_class
from utils.error.exception import NoUpdatePlayer, NoUpdateClan


# @dataclass
class ClanMember(PlayerModel, Tank):
    all: dict
    data_time: str = ""
    tank_id: int = 1111

    def __init__(self, nickname, id, all):
        super().__init__(nickname, id, "", all)
        Tank.__init__(self, tank_id=1, all=all)
        self.data_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __post_init__(self):
        for key, value in self.all.items():
            setattr(self, key, value)

    def __get_name(self):
        self.data["nickname"] = self.nickname

    def _calculation(self):
        self._get_battles()
        self._get_wins()
        self._get_damage()
        self._get_accuracy()
        self._get_survival()
        self._get_efficiency()
        self._update_class(
            battles=self._battles,
            wins=self._wins,
            damage=self._damage,
            shots=self._shots,
            hits=self._hits,
            survival=self._survival if hasattr(self, "_survival") else 0,
            received=self._damage_received,
        )

    def _get_results(self):
        if self.other == self:
            raise NoUpdatePlayer("No update")
        self.__get_name()
        self._calculation()

    def result(self, other) -> dict:
        return super().result(other)


@dataclass
class Clan(Data_class):
    clan_id: int
    tag: str
    name: str
    data: str
    players: list[dict]
    __error_message: list[str] = field(init=False, default_factory=list)
    _data: dict = field(init=False, default_factory=dict)

    def result(self, other):
        return super().result(other)

    @classmethod
    def general(cls):
        return super().general()
