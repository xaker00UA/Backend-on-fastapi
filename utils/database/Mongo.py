import os
from typing import AsyncGenerator
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorCursor,
)

from .helper import get_clan_rating_pipeline
from utils.settings.logger import LoggerFactory
from ..models.player import UserDB, Tank
from ..models.clan import ClanDB


class Connect:
    client = AsyncIOMotorClient(os.getenv("MONGO", "mongodb://localhost:27017/"))
    db = client[os.getenv("NAME_DB", "wotblitz")]

    @classmethod
    async def add(cls, data):
        pass


class Player_sessions(Connect):
    collection: AsyncIOMotorCollection = Connect.db["Session"]

    @classmethod
    async def get(cls, name, id, region, access_token) -> UserDB:
        filter = {
            "$or": [
                {"player_id": id, "region": region},
                {
                    "name": {"$regex": f"^{name}$", "$options": "i"},
                    "region": region,
                },
            ]
        }
        if access_token is not None:
            filter["$or"].append({"access_token": access_token})
        res = await cls.collection.find_one(
            filter=filter,
        )
        if res:
            res = UserDB.model_validate(res)
        return res

    @classmethod
    async def add(cls, user: UserDB) -> UserDB:

        await cls.collection.replace_one(
            filter={"player_id": user.player_id},
            replacement=user.model_dump(),
            upsert=True,
        )
        return user

    @classmethod
    async def update(cls, user: UserDB) -> UserDB:
        existing_document = await cls.collection.find_one({"player_id": user.player_id})
        if existing_document:
            await cls.collection.update_one(
                {"player_id": user.player_id},
                {"$set": {"access_token": user.access_token}},
            )
        else:
            await cls.add(user)
        return user

    @classmethod
    async def gets(cls, user: UserDB) -> list[UserDB]:
        res = await cls.collection.find(
            filter={"name": {"$regex": user.name, "$options": "i"}},
            projection={"name": 1, "_id": 0, "region": 1, "player_id": 1},
        ).to_list(length=10)
        return [UserDB.model_validate(doc) for doc in res]

    @classmethod
    async def find_all(cls) -> AsyncGenerator[list[UserDB], None]:
        cursor: AsyncIOMotorCursor = cls.collection.find()
        batch_size = 100

        while True:
            batch = await cursor.to_list(length=batch_size)
            if not batch:
                break
            yield [UserDB.model_validate(doc) for doc in batch]


class Clan_sessions(Connect):
    collection: AsyncIOMotorCollection = Connect.db["Clan"]

    @classmethod
    async def get(cls, name: str, clan_id, region) -> ClanDB:
        filter_conditions = []

        if clan_id and region:
            filter_conditions.append({"clan_id": clan_id, "region": region})

        if name:
            filter_conditions.append(
                {"name": {"$regex": f"^{name}$", "$options": "i"}, "region": region}
            )
            filter_conditions.append(
                {
                    "tag": {"$regex": f"^{name.upper()}$", "$options": "i"},
                    "region": region,
                }
            )

        # Объединяем условия с оператором "$or"
        filter = {"$or": filter_conditions}
        res = await cls.collection.find_one(filter=filter)
        if res:
            return ClanDB(**res)

    @classmethod
    async def add(cls, clan: ClanDB) -> ClanDB:
        await cls.collection.replace_one(
            filter={"clan_id": clan.clan_id},
            replacement=clan.model_dump(),
            upsert=True,
        )
        return clan

    @classmethod
    async def gets(cls, name) -> list[ClanDB]:
        filter = {
            "$or": [
                {"name": {"$regex": name, "$options": "i"}},
                {"tag": {"$regex": name, "$options": "i"}},
            ]
        }
        res = await cls.collection.find(
            filter=filter,
        ).to_list(length=10)
        return [ClanDB.model_validate(doc) for doc in res]

    @classmethod
    async def find_all(cls) -> AsyncGenerator[list, None]:
        cursor: AsyncIOMotorCursor = cls.collection.find()
        batch_size = 100

        while True:
            batch = await cursor.to_list(length=batch_size)
            if not batch:
                break
            yield [ClanDB.model_validate(doc) for doc in batch]


class Player_all_sessions(Player_sessions):
    collection: AsyncIOMotorCollection = Connect.db["Session_all"]

    @classmethod
    async def add(cls, user: list[UserDB]) -> UserDB:
        users = [i.model_dump() for i in user]
        await cls.collection.insert_many(users)

    @classmethod
    async def get(cls, user: UserDB, timestamp_ago: int) -> UserDB:
        filter = {
            "$and": [
                {"player_id": user.player_id},
                {"timestamp": {"$lte": timestamp_ago}},
            ]
        }
        res = await cls.collection.find_one(filter=filter, sort=[("timestamp", -1)])
        if res:
            return UserDB.model_validate(res)

    @classmethod
    async def get_top(cls, parameter, start_day, limit=10):
        base_match = {"$match": {"timestamp": {"$gte": start_day}}}
        base_sort = {"$sort": {"timestamp": 1}}

        base_group = {
            "$group": {
                "_id": "$player_id",
                "name": {"$last": "$name"},
                "region": {"$last": "$region"},
                "lastBattle": {"$last": "$acount.statistics.all.battles"},
                "firstBattle": {"$first": "$acount.statistics.all.battles"},
                "lastWins": {"$last": "$acount.statistics.all.wins"},
                "firstWins": {"$first": "$acount.statistics.all.wins"},
                "lastDamage": {"$last": "$acount.statistics.all.damage_dealt"},
                "firstDamage": {"$first": "$acount.statistics.all.damage_dealt"},
            }
        }

        pipeline = [base_match, base_sort, base_group]

        if parameter == "battles":
            pipeline += [
                {
                    "$project": {
                        "name": 1,
                        "region": 1,
                        "_id": 1,
                        "battles": {"$subtract": ["$lastBattle", "$firstBattle"]},
                    }
                },
                {"$sort": {"battles": -1}},
            ]

        elif parameter in ("wins", "damage"):
            value_key = "wins" if parameter == "wins" else "damage"
            last_key = "$lastWins" if parameter == "wins" else "$lastDamage"
            first_key = "$firstWins" if parameter == "wins" else "$firstDamage"

            delta_battles = {"$subtract": ["$lastBattle", "$firstBattle"]}
            delta_value = {"$subtract": [last_key, first_key]}

            formula = (
                {
                    "$multiply": [
                        {"$divide": [delta_value, delta_battles]},
                        100,
                    ]
                }
                if parameter == "wins"
                else {"$divide": [delta_value, delta_battles]}
            )

            pipeline += [
                {"$match": {"$expr": {"$gt": [delta_battles, 20]}}},
                {
                    "$project": {
                        "name": 1,
                        "region": 1,
                        value_key: {
                            "$round": [
                                {"$cond": [{"$eq": [delta_battles, 0]}, 0, formula]},
                                2,
                            ]
                        },
                    }
                },
                {"$sort": {value_key: -1}},
            ]

        else:
            raise TypeError("Parameter not found")

        pipeline += [{"$limit": limit}]

        res = cls.collection.aggregate(pipeline)
        return await res.to_list()


class Clan_all_sessions(Clan_sessions):
    collection: AsyncIOMotorCollection = Connect.db["Clan_all"]

    @classmethod
    async def add(cls, clan: ClanDB) -> ClanDB:
        await cls.collection.insert_one(clan.model_dump())
        return clan

    @classmethod
    async def get_top(cls, end_day, start_day, limit=10):
        pipeline = get_clan_rating_pipeline(start_day, end_day)
        return await cls.collection.aggregate(pipeline).to_list(length=limit)


class Tank_DB(Connect):
    collection: AsyncIOMotorCollection = Connect.db["Tank"]

    @classmethod
    async def get_by_id(cls, id: int | Tank) -> dict:
        if isinstance(id, Tank):
            id = Tank.tank_id
        res = await cls.collection.find_one(filter={"tank_id": id})
        if res is not None:
            del res["_id"]
            res["level"] = res.pop("tier")
        else:
            res = {"level": "undefined", "name": "undefined"}
            LoggerFactory.warn(f"Танк не найден с параметрами id={id}")
        return res

    @classmethod
    async def get_list_id(cls, id: list[int]):
        res = await cls.collection.find({"tank_id": {"$in": id}}).to_list(length=None)

        # Преобразование полученных данных в словарь
        for item in res:
            item["level"] = item.pop("tier")
        data = {item["tank_id"]: item for item in res}
        # Для каждого ID, для которого нет данных, добавляем дефолтный словарь
        for tank_id in id:
            if tank_id not in data:
                data[tank_id] = {"level": "undefined", "name": "undefined"}
                LoggerFactory.warn(f"Танк не найден с параметрами id={tank_id}")

        return data

    @classmethod
    async def add(cls, tank: dict | list[dict]) -> Tank:
        cls.collection.replace_one(filter={"tank_id": tank["tank_id"]})
