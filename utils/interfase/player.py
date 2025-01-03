from asyncio import gather
import asyncio
from ..models import (
    PlayerDetails,
    PlayerGeneral,
    User,
    Tank,
    Rating,
    PlayerModel,
    RestPlayer,
)
from ..database.Mongo import Player_sessions, Tank_DB, Player_all_sessions
from ..api.wotb import APIServer
from ..error import *
import logging

logger = logging.getLogger()


class PlayerSession:
    def __init__(
        self,
        name: str = None,
        id: int = None,
        reg: str = "eu",
        access_token: str = None,
    ):
        if name is None and id is None and access_token is None:
            raise ValueError("Either name or id must be provided")
        self.name = name
        self.id = id
        self.region = reg
        self.session = APIServer()
        self.details = PlayerDetails
        self.general = PlayerGeneral
        self.user: User | None = User(
            region=reg, name=name, player_id=id, access_token=access_token
        )
        self.old_user: User | None = None
        self.settings = None

    async def add_player(self):
        try:
            await self.get_player_details()
            await Player_sessions.update(self.user)
            return True
        except PlayerNotFound:
            return "Игрок не найден"
        except Exception as e:
            return str(e)
            # TODO: logging exception

    async def get_player_DB(self):
        self.old_user = await Player_sessions.get(
            self.name, self.id, self.region, self.user.access_token
        )
        if not self.old_user:
            raise NotFoundPlayerDB(
                self.name, self.id, self.region, self.user.access_token
            )

    async def get_player_info(self) -> User:
        try:
            data = await self.session.get_general(self.user)
        except RequestError as e:
            message = str(e)
            if "INVALID access_token" in message:
                self.user.access_token = None
                data = await self.session.get_general(self.user)
            else:
                raise RequestError(message)
        self.user = data
        return self.user

    async def get_player_details(self, rating=True):
        try:
            data = await self.session.get_details_tank(self.user, rating=rating)
        except RequestError as e:
            message = str(e)
            if "INVALID access_token" in message:
                self.user.access_token = None
                data = await self.session.get_general(self.user)
            else:
                raise RequestError(message)
        self.user = data

    async def _results(self):
        try:
            await self.get_player_DB()
        except NotFoundPlayerDB:
            await self.session.get_id(self.user.region, self.user.name)
            raise NotFoundPlayerDB

        self.user: User = await self.session.get_details_tank(self.old_user)
        user = self.user - self.old_user
        data = user.acount.result()
        res = RestPlayer(
            id=self.user.player_id, name=self.user.name, region=self.user.region, **data
        )
        tasks = [Tank_DB.get_by_id(tank["tank_id"]) for tank in res.tanks]
        tanks = await gather(*tasks)
        for tank, db_tank in zip(res.tanks, tanks):
            tank.update(db_tank)
        return res

    async def results(self) -> set[RestPlayer, RestPlayer, PlayerDetails]:
        session = await self._results()
        if not isinstance(session, str):
            updated = await self.update_stats(session)
            return session, updated, self.user.acount.result()
        else:
            return (session,)

    async def reset(self):
        await self.get_player_DB()
        self.user = await self.session.get_details_tank(self.old_user)
        await Player_sessions.add(self.user)
        return None

    async def update_stats(self, object: RestPlayer):
        new = self.user.acount.result()
        old = self.old_user.acount.result()
        tank_id = [tank_id["tank_id"] for tank_id in object.tanks]
        new["tanks"] = [tank for tank in new["tanks"] if tank["tank_id"] in tank_id]
        old["tanks"] = [tank for tank in old["tanks"] if tank["tank_id"] in tank_id]
        new = RestPlayer(
            id=self.user.player_id, region=self.region, name=self.user.name, **new
        )
        old = RestPlayer(
            id=self.user.player_id, region=self.region, name=self.user.name, **old
        )
        res = old - new
        for i in res.tanks:
            for j in object.tanks:
                if i["tank_id"] == j["tank_id"]:
                    i["tier"] = j["tier"]
                    i["name"] = j["name"]
        return res

    async def logout(self):
        await self.get_player_DB()
        await self.session.logout(self.old_user.region, self.old_user.access_token)
        self.old_user.access_token = None
        await Player_sessions.update(self.old_user)

    async def get_players(self) -> list[User] | list:
        return await Player_sessions.gets(self.user)

    async def _get_attributes(self):
        self.attributes = await self.settings.get_params()
        # TODO: Implement settings and attributes loading

    async def get_session(self) -> dict:
        pass

    @classmethod
    async def update_db(cls):
        logger.info("Start update players DB")
        async for batch in Player_sessions.find_all():
            tasks = []
            users = []
            semaphore = asyncio.Semaphore(10)

            async def semaphore_task(task):
                async with semaphore:
                    await task

            for user in batch:
                user = cls(name=user.name, reg=user.region, id=user.player_id)
                users.append(user)
                tasks.append(user.get_player_details(rating=False))

            for task in asyncio.as_completed([semaphore_task(task) for task in tasks]):
                await task
            await gather(*[Player_all_sessions.add(user.user) for user in users])
        logger.info("End update players DB")
