from asyncio import gather
import asyncio
from datetime import datetime, timedelta
from itertools import zip_longest

from utils.models.respnse_model import General, RestUser
from ..models import (
    PlayerDetails,
    UserDB,
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
    session = APIServer()

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

        self.details = PlayerDetails
        self.user: UserDB | None = UserDB(
            region=reg, name=name, player_id=id, access_token=access_token
        )
        self.old_user: UserDB | None = None
        self.settings = None

    async def add_player(self):
        await self.get_player_details()
        await Player_sessions.update(self.user)
        return True

    async def get_player_DB(self):
        self.old_user = await Player_sessions.get(
            self.name, self.id, self.region, self.user.access_token
        )
        if not self.old_user:
            raise NotFoundPlayerDB(
                name=self.name,
                player_id=self.id,
                region=self.region,
                access_token=self.user.access_token,
            )

    async def get_player_info(self) -> UserDB:
        try:
            data = await self.session.get_general(self.user)
        except RequestError as e:
            message = str(e)
            if "INVALID_ACCESS_TOKEN" in message:
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
            if "INVALID_ACCESS_TOKEN" in message:
                self.user.access_token = None
                data = await self.session.get_details_tank(self.user)
            else:
                raise RequestError(message)
        self.user = data

    async def _results(self, trigger: bool = True):
        if trigger:
            try:
                await self.get_player_DB()
            except NotFoundPlayerDB:
                player_id = await self.session.get_id(self.user.region, self.user.name)
                self.id = player_id
                await self.get_player_DB()

            self.user: UserDB = await self.session.get_details_tank(self.old_user)
        user = self.user - self.old_user
        model = user.result()
        return model

    async def results(self, trigger: bool = True) -> RestPlayer:
        session = await self._results(trigger=trigger)
        now = await self._now_stats()
        update = await self._update_stats()
        if now.tanks.now:
            tasks = [tank.tank_id for tank in now.tanks.now]
            data = await Tank_DB.get_list_id(tasks)

            def update_object_with_data(obj):
                if obj and obj.tank_id in data:
                    obj.__dict__.update(data[obj.tank_id])

            for ses, now_item, upd in zip_longest(
                session.tanks.session,
                now.tanks.now,
                update.tanks.session,
                fillvalue=None,
            ):
                update_object_with_data(ses)
                update_object_with_data(now_item)
                update_object_with_data(upd)
        session = self.update_model_rest(session, update, now, "general")
        session = self.update_model_rest(session, update, now, "tanks")

        return session

    @staticmethod
    def update_model_rest(session, update, now, field_name):
        data = {
            "update": getattr(update, field_name).session,
            "session": getattr(session, field_name).session,
            "now": getattr(now, field_name).now,
        }
        validated_data = General.model_validate(data)
        return session.model_copy(update={field_name: validated_data}, deep=True)

    async def reset(self):
        await self.get_player_DB()
        self.user = await self.session.get_details_tank(self.old_user)
        await Player_sessions.add(self.user)
        return None

    async def _now_stats(self):
        now = self.user.result("now")
        return now

    async def _update_stats(self):
        old = self.old_user.result()
        now = self.user.result()
        update = now - old
        return update

    async def logout(self):
        await self.get_player_DB()
        await self.session.logout(self.old_user.region, self.old_user.access_token)
        self.old_user.access_token = None
        await Player_sessions.update(self.old_user)

    async def get_players(self) -> list[UserDB] | list:
        return await Player_sessions.gets(self.user)

    async def top_players_server(self):
        pass

    async def _get_attributes(self):
        self.attributes = await self.settings.get_params()
        # TODO: Implement settings and attributes loading

    async def get_session(self) -> dict:
        pass

    async def get_period(self, start_day: int, end_day: int) -> RestUser:
        await self.get_player_DB()
        self.user = await Player_all_sessions.get(self.user, end_day)
        if not self.user:
            raise NotFoundPeriod(self.name)
        self.old_user = await Player_all_sessions.get(self.user, start_day)
        if not self.old_user:
            raise NotFoundPeriod(self.name)
        return await self.results(trigger=False)

    @classmethod
    async def get_token(self, region, redirect_url):
        return await self.session.get_token(redirect_url=redirect_url, reg=region)

    @classmethod
    async def top_players(cls, limit, parameter, start_day):
        return await Player_all_sessions.get_top(
            limit=limit,
            parameter=parameter,
            start_day=start_day,
        )

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
