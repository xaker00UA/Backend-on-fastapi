from datetime import datetime
from pydantic import BaseModel, Field, field_serializer, field_validator

from utils.models.tank import PlayerModel
from utils.models.response_model import BaseStats, RestClan, RestMember
from utils.models.base_models import Session


class Clan(BaseModel):
    name: str
    clan_id: int
    created_at: int
    tag: str
    members_count: int


class ClanDetails(BaseModel):
    clan_id: int
    created_at: int
    creator_id: int
    creator_name: str
    description: str
    emblem_set_id: int
    members_count: int
    members_ids: list[int]
    motto: str
    name: str
    old_name: str | None
    old_tag: str | None
    tag: str


class ClanDB(BaseModel, Session):
    region: str
    name: str
    clan_id: int
    tag: str
    members_count: int
    members: list[PlayerModel]
    timestamp: int = Field(default_factory=lambda: int(datetime.now().timestamp()))

    def sum_general(self, members: list[RestMember]) -> BaseStats:
        total_battles = sum(s.general.all.battles for s in members if s.general.all)
        if total_battles == 0:
            return BaseStats()

        def weighted_sum(attr: str) -> float:
            return sum(
                getattr(s.general.all, attr) * s.general.all.battles
                for s in members
                if (s.general.all)
            )

        return BaseStats(
            battles=total_battles,
            winrate=round(weighted_sum("winrate") / total_battles, 2),
            damage=round(weighted_sum("damage") / total_battles, 2),
            accuracy=round(weighted_sum("accuracy") / total_battles, 2),
            survival=round(weighted_sum("survival") / total_battles, 2),
            avg_xp=round(weighted_sum("avg_xp") / total_battles, 2),
            wins_and_survived=round(
                weighted_sum("wins_and_survived") / total_battles, 2
            ),
            murder_to_murder=round(weighted_sum("murder_to_murder") / total_battles, 2),
            damage_coefficient=round(
                weighted_sum("damage_coefficient") / total_battles, 2
            ),
        )

    def __sub__(self, other: "ClanDB") -> RestClan:
        if super().__sub__(other):
            timestamp = abs(self.timestamp - other.timestamp)
            # self.members[0].account_id
            other_members = {obj.account_id: obj for obj in other.members}
            self_members = {obj.account_id: obj for obj in self.members}
            common_keys = set(self_members.keys()) & set(other_members.keys())
            members = []
            members_update = []
            for key in common_keys:
                res = self_members[key] - other_members[key]
                members_update.append(res)
                res = res.result()
                if res.general.session.all or res.general.session.rating:
                    result = RestMember(
                        id=res.player_id,
                        nickname=res.name,
                        general=res.general.session,
                        last_battle_time=0,
                    )
                    members.append(result)

            data = self.model_dump(exclude={"members", "members_count", "timestamp"})
            return RestClan(
                members=members,
                time=timestamp,
                members_count=self.members_count,
                general=self.sum_general(members),
                **data,
            )

    def result() -> RestClan:
        pass


class ClanTop(BaseModel):
    region: str
    name: str
    clan_id: int
    tag: str
    general_battles: int
    general_wins: float
    averageDamage: float
    rating: float

    @field_validator("rating", mode="before")
    def round_rating(cls, v):
        return round(v, 4)

    @field_serializer("general_wins")
    def valid_wins(self, v):
        if v < 0:
            return 100 * v
        return v
