from typing import AsyncGenerator
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorCursor,
)
import os
from ..models import UserDB, Tank
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
            projection={"name": 1, "_id": 0, "region": 1},
        ).to_list(length=10)
        return [UserDB.model_validate(doc) for doc in res]

    @classmethod
    async def find_all(cls) -> AsyncGenerator[list, None]:
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
    async def add(cls, user: UserDB) -> UserDB:
        await cls.collection.insert_one(user.model_dump())
        return user

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
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_day}}},
            {"$sort": {"timestamp": 1}},
            {
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
            },
        ]

        if parameter == "battles":
            pipeline.append(
                {
                    "$project": {
                        "name": 1,
                        "region": 1,
                        "battles": {"$subtract": ["$lastBattle", "$firstBattle"]},
                    }
                }
            )
            pipeline.append({"$sort": {"battles": -1}})

        elif parameter == "wins":
            pipeline.append(
                {
                    "$project": {
                        "name": 1,
                        "region": 1,
                        "wins": {
                            "$round": [
                                {
                                    "$cond": [
                                        {
                                            "$eq": [
                                                {
                                                    "$subtract": [
                                                        "$lastBattle",
                                                        "$firstBattle",
                                                    ]
                                                },
                                                0,
                                            ]
                                        },
                                        0,
                                        {
                                            "$multiply": [
                                                {
                                                    "$divide": [
                                                        {
                                                            "$subtract": [
                                                                "$lastWins",
                                                                "$firstWins",
                                                            ]
                                                        },
                                                        {
                                                            "$subtract": [
                                                                "$lastBattle",
                                                                "$firstBattle",
                                                            ]
                                                        },
                                                    ]
                                                },
                                                100,
                                            ]
                                        },
                                    ]
                                },
                                2,
                            ]
                        },
                    }
                }
            )
            pipeline.append({"$sort": {"wins": -1}})

        elif parameter == "damage":
            pipeline.append(
                {
                    "$project": {
                        "name": 1,
                        "region": 1,
                        "damage": {
                            "$round": [
                                {
                                    "$cond": [
                                        {
                                            "$eq": [
                                                {
                                                    "$subtract": [
                                                        "$lastBattle",
                                                        "$firstBattle",
                                                    ]
                                                },
                                                0,
                                            ]
                                        },
                                        0,
                                        {
                                            "$divide": [
                                                {
                                                    "$subtract": [
                                                        "$lastDamage",
                                                        "$firstDamage",
                                                    ]
                                                },
                                                {
                                                    "$subtract": [
                                                        "$lastBattle",
                                                        "$firstBattle",
                                                    ]
                                                },
                                            ]
                                        },
                                    ]
                                },
                                2,
                            ]
                        },
                    }
                }
            )
            pipeline.append(
                {"$sort": {"damage": -1}},
            )

        else:
            raise TypeError("Parameter not found")

        pipeline.extend([{"$limit": limit}, {"$project": {"_id": 0}}])

        res = cls.collection.aggregate(pipeline)
        return await res.to_list()


class Clan_all_sessions(Clan_sessions):
    collection: AsyncIOMotorCollection = Connect.db["Clan_all"]

    @classmethod
    async def add(cls, clan: ClanDB) -> ClanDB:
        await cls.collection.insert_one(clan.model_dump())
        return clan


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
        return res

    @classmethod
    async def get_list_id(cls, id: list[int]):
        res = await cls.collection.find({"tank_id": {"$in": id}}).to_list(length=None)

        # Преобразование полученных данных в словарь
        data = {item["tank_id"]: item for item in res}

        # Для каждого ID, для которого нет данных, добавляем дефолтный словарь
        for tank_id in id:
            if tank_id not in data:
                data[tank_id] = {"level": "undefined", "name": "undefined"}

        return data

    @classmethod
    async def add(cls, tank: dict | list[dict]) -> Tank:
        cls.collection.replace_one(filter={"tank_id": tank["tank_id"]})
