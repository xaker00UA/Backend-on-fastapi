from asyncio import gather
from itertools import zip_longest
import traceback

from pydantic import BaseModel

from utils.database.admin import add_active_user
from utils.models.response_model import General, Medal, Medals, RestUser, TopPlayer
from ..models.player import (
    PlayerDetails,
    UserDB,
    RestPlayer,
)
from ..database.Mongo import Player_sessions, Tank_DB, Player_all_sessions, Medal_DB
from ..api.wotb import APIServer
from ..error import *


from ..settings.logger import LoggerFactory


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
        LoggerFactory.log(
            f"Пользователь с параметрами: name={self.name}, id={self.id}, region={self.region}, access_token={access_token}",
            level="DEBUG",
        )

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
        except InvalidAccessToken as e:
            self.user.access_token = None
            data = await self.session.get_general(self.user)
        self.user = data
        await self.get_player_medal()
        return self.user

    async def get_player_details(self, rating=True):
        try:
            data = await self.session.get_details_tank(self.user, rating=rating)
        except InvalidAccessToken as e:
            self.user.access_token = None
            data = await self.session.get_details_tank(self.user)
        self.user = data
        await self.get_player_medal()

    async def get_player_medal(self):
        data = await self.session.get_medal(self.user)
        medal_db = await Medal_DB.get_list(list(data.keys()))
        medals = []
        for key, val in data.items():
            image = medal_db.get(key)
            if image is None or not isinstance(image, str):
                image = "https://example.com/default-image.png"
            medals.append(Medal(name=key, count=val, image=image))

        medals = Medals(medals=medals)
        self.user.medal = medals

    async def _results(self, trigger: bool = True):
        if trigger:
            try:
                await self.get_player_DB()
                self.user.player_id = self.old_user.player_id
            except NotFoundPlayerDB:
                player_id = await self.session.get_id(self.user.region, self.user.name)
                self.id = player_id
                await self.get_player_DB()

            await self.get_player_details()

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

            def update_object_with_data(obj: BaseModel, update=None):
                if obj is None:
                    return
                if update is None and hasattr(obj, "tank_id") and obj.tank_id in data:
                    update = data[obj.tank_id]
                if not update:
                    return
                for key, value in update.items():
                    if not hasattr(obj, key):
                        continue
                    current = getattr(obj, key)
                    if isinstance(current, BaseModel) and isinstance(value, dict):
                        update_object_with_data(current, value)
                    else:
                        setattr(obj, key, value)

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

    async def reset(self, isAdmin=False):
        await self.get_player_DB()
        self.user = await self.session.get_details_tank(self.old_user)
        await Player_sessions.add(self.user)
        if not isAdmin:
            data = {
                "player_id": self.user.player_id,
                "name": self.user.name,
                "region": self.user.region,
            }
            add_active_user(**data)
            LoggerFactory.log("User reset stats", extra=data)
        else:
            LoggerFactory.log("Admin reset stats", extra=data)
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

    async def get_period(self, start_day: int, end_day: int) -> RestUser:
        await self.get_player_DB()
        self.user = await Player_all_sessions.get(self.old_user, end_day)
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
        data = await Player_all_sessions.get_top(
            limit=limit,
            parameter=parameter,
            start_day=start_day,
        )
        return [
            TopPlayer(
                region=item.get("region"),  # type ignore
                name=item.get("name"),
                player_id=item.get("_id"),
                parameter=parameter,  # type ignore
                value=item.get(parameter),
            )
            for item in data
        ]

    @classmethod
    async def update_db(cls):
        LoggerFactory.log("Start update players DB")
        async for batch in Player_sessions.find_all():
            tasks = []
            users = []

            for user in batch:
                user = cls(
                    name=user.name,
                    reg=user.region,
                    id=user.player_id,
                    access_token=user.access_token,
                )
                tasks.append(user.get_player_details(rating=False))
                users.append(user)
            update_users = await gather(*tasks, return_exceptions=True)
            for i in update_users:
                if isinstance(i, Exception):
                    print(i.with_traceback())
                    print("Traceback:\n", traceback.format_exc())

                    LoggerFactory.log(str(i), level="ERROR")
            await Player_all_sessions.add([user.user for user in users])
        LoggerFactory.log("End update players DB")

    @classmethod
    async def update_player_token(cls):
        LoggerFactory.log("Start update player token")
        async for batch in Player_sessions.find_all():
            tasks = []

            for user in batch:
                if user.access_token is None:
                    continue
                tasks.append(cls.session.longer_token(user))
            updated_players = await gather(*tasks)

            await gather(
                *[Player_sessions.update(player) for player in updated_players]
            )
        LoggerFactory.log("End update player token")
