from datetime import datetime
from pydantic import BaseModel, Field

from utils.models.tank import PlayerModel
from .respnse_model import RestClan, RestMember
from .base_models import Session


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

    def __sub__(self, other: "ClanDB") -> RestClan:
        if super().__sub__(other):
            timestamp = abs(self.timestamp - other.timestamp)
            self.members[0].account_id
            other_members = {obj.account_id: obj for obj in other.members}
            self_members = {obj.account_id: obj for obj in self.members}
            common_keys = set(self_members.keys()) & set(other_members.keys())
            members = []
            for key in common_keys:
                res = self_members[key] - other_members[key]
                res = res.result()
                if res.general.session.all or res.general.session.rating:
                    result = RestMember(
                        id=res.id,
                        nickname=res.name,
                        general=res.general.session,
                        last_battle_time=0,
                    )
                    members.append(result)

            data = self.model_dump(exclude={"members", "members_count", "timestamp"})
            return RestClan(
                members=members, time=timestamp, members_count=len(members), **data
            )

    def result() -> RestClan:
        pass
