import asyncio
from typing import Literal
from pydantic import BaseModel, computed_field
from utils.cache.redis_cache import redis_cache
from utils.database.Mongo import (
    Clan_all_sessions,
    Clan_sessions,
    Player_all_sessions,
    Player_sessions,
)
from utils.interface.clan import ClanInterface
from utils.interface.player import PlayerSession
from uuid import uuid4
from loguru import logger


class Task(BaseModel):
    id: str
    status: Literal["pending", "done"]
    total_tasks: int
    done_tasks: int

    def add_done_task(self):
        self.done_tasks += 1

    def done(self):
        self.status = "done"

    @computed_field
    def progress(self) -> float:
        try:
            return round((self.done_tasks / self.total_tasks), 2)
        except ZeroDivisionError:
            return 0


class TaskInterface:
    def __init__(self):
        self.player_interface: type[PlayerSession] = PlayerSession
        self.clan_interface: type[ClanInterface] = ClanInterface
        self.cash = redis_cache

    def create_key(self) -> str:
        return str(uuid4())

    async def create_task(self, flag: Literal["player", "clan"]):
        _id = self.create_key()
        if flag == "player":
            task = Task(
                id=_id,
                status="pending",
                total_tasks=await self.count_player(),
                done_tasks=0,
            )
        else:
            task = Task(
                id=_id,
                status="pending",
                total_tasks=await self.count_clan(),
                done_tasks=0,
            )
        await self.set_task(task)
        return task

    async def get_task(self, _id: str) -> Task:
        data = await self.cash.get(_id)
        return Task.model_validate(data)

    async def set_task(self, task: Task):
        await self.cash.set(task.id, task.model_dump_json())

    async def count_player(self):
        return await Player_sessions.collection.count_documents({})

    async def count_clan(self):
        return await Clan_sessions.collection.count_documents({})

    async def update_clan_db(self, _id: str, _all: bool = True):
        if _all:
            logger.info("Start update clan all db")
            logger.info("Start update clan db")
        else:
            logger.info("Start update clan all db")
        async for batch in Clan_sessions.find_all():
            for clan in batch:
                clan = await self.clan_interface(
                    name=clan.name, region=clan.region, clan_id=clan.clan_id
                ).get_clan_details()
                if _all:
                    await Clan_sessions.add(clan)
                await Clan_all_sessions.add(clan)
                task = await self.get_task(_id)
                task.add_done_task()
                await self.set_task(task)
        task = await self.get_task(_id)
        task.done()
        await self.set_task(task)
        if _all:
            logger.info("End update clan all db")
            logger.info("End update clan db")
        else:
            logger.info("End update clan all db")

    async def update_player_db(self, _id: str, _all: bool = True):
        if _all:
            logger.info("Start update player all db")
            logger.info("Start update player db")
        else:
            logger.info("Start update player all db")
        semaphore = asyncio.Semaphore(4)

        async def process_user(user_data):
            async with semaphore:
                user = self.player_interface(
                    name=user_data.name,
                    reg=user_data.region,
                    id=user_data.player_id,
                    access_token=user_data.access_token,
                )
                try:
                    await user.get_player_details()
                    if _all:
                        await Player_sessions.add(user.user)
                    await Player_all_sessions.add([user.user])

                    task = await self.get_task(_id)
                    task.add_done_task()
                    await self.set_task(task)
                except Exception as e:
                    logger.critical("Exception: {}", str(e))

        tasks = []
        async for batch in Player_sessions.find_all():
            for user_data in batch:
                tasks.append(process_user(user_data))

        await asyncio.gather(*tasks)  # ✅ запускаем всё параллельно
        task = await self.get_task(_id)
        task.done()
        await self.set_task(task)
        if _all:
            logger.info("End update player all db")
            logger.info("End update player db")
        else:
            logger.info("End update player all db")

    async def reset(self, flag: Literal["player", "clan"], **kwargs):
        task = Task(id=self.create_key(), status="done", total_tasks=1, done_tasks=1)
        await self.set_task(task)
        if flag == "player":
            asyncio.create_task(self.player_interface(**kwargs).reset())
        else:
            asyncio.create_task(self.clan_interface(**kwargs).reset())
        return task
