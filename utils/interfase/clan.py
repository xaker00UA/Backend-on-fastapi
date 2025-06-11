from asyncio import gather

from utils.settings.logger import LoggerFactory
from ..models.clan import Clan, ClanDB, ClanDetails, ClanTop, RestClan
from ..database.Mongo import Clan_sessions, Clan_all_sessions
from ..api.wotb import APIServer
from .player import PlayerSession
from ..error import *


class ClanInterface:
    def __init__(self, name=None, clan_id=None, tag=None, region="eu"):
        if name is not None and tag is not None and clan_id is not None:
            raise ValueError("Either name or id must be provided")
        self.name = name
        self.clan_id = clan_id
        self.tag = tag
        self.region = region
        self.session = APIServer()
        self.player_interface = PlayerSession
        LoggerFactory.log(
            f"Клан с параметрами tag={self.tag}, clan_id={self.clan_id}, name={self.name}, region={self.region}",
            level="DEBUG",
        )

    async def get_clan_info(self) -> Clan:
        res = await self.session.get_clan_info(
            name=self.name if self.name else self.tag, region=self.region
        )
        return res

    async def _get_clan_details(self) -> ClanDetails:
        if self.clan_id:
            res = await self.session.get_clan_details(
                clan_id=self.clan_id, region=self.region
            )
        else:
            res = await self.session.get_clan_details(
                name=self.name if self.name else self.tag, region=self.region
            )
        return res

    async def get_clan_details(self) -> ClanDB:
        res = await self._get_clan_details()
        task = [
            self.player_interface(id=player_id, reg=self.region).get_player_info()
            for player_id in res.members_ids
        ]
        data = await gather(*task, return_exceptions=True)
        data = [
            result for result in data if not isinstance(result, BaseCustomException)
        ]
        data = [user.acount for user in data]
        return ClanDB(**res.model_dump(), members=data, region=self.region)

    async def reset(self):
        await self.add_clan_db()

    async def results(self) -> RestClan:
        old_clan = await self.get_clan_db()
        now_clan = await self.get_clan_details()

        return now_clan - old_clan

    async def get_clan_db(self) -> ClanDB:
        res = await Clan_sessions.get(self.name, self.clan_id, self.region)
        if not res:
            await self.add_clan_db()
            raise NotFoundClanDB(self.name if self.name else self.tag)
        return res

    async def add_clan_db(self) -> ClanDB:
        res = await self.get_clan_details()
        res = await Clan_sessions.add(res)
        return res

    async def get_clans(self) -> list[ClanDB]:
        return await Clan_sessions.gets(self.name)

    @classmethod
    async def get_top_list_clan(cls, end_day, start_day, limit) -> list:
        data = await Clan_all_sessions.get_top(
            end_day=end_day, start_day=start_day, limit=limit
        )
        return [ClanTop.model_validate(i) for i in data]

    @classmethod
    async def update_db(cls):
        LoggerFactory.log("Start update clan db")
        async for batch in Clan_sessions.find_all():
            for clan in batch:
                clan = await cls(
                    name=clan.name, region=clan.region, clan_id=clan.clan_id
                ).get_clan_details()
                await gather(
                    *[Clan_all_sessions.add(clan), Clan_sessions.add(clan)],
                    return_exceptions=True,
                )
        LoggerFactory.log("End update clan db")
