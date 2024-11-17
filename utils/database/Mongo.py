from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
import asyncio
import os

from ..models import User, Tank


class Connect:
    client = AsyncIOMotorClient(os.getenv("MONGO", "mongodb://localhost:27017/"))
    db = client.test_db

    @classmethod
    async def add(cls, data):
        pass


class Player_sessions(Connect):
    collection: AsyncIOMotorCollection = Connect.db["Session"]

    @classmethod
    async def get(cls, name, id, region, access_token) -> User:
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
            user = User.model_validate(res)
        else:
            user = None
        return user

    @classmethod
    async def add(cls, user: User) -> User:
        await cls.collection.replace_one(
            filter={"player_id": user.player_id},
            replacement=user.model_dump(),
            upsert=True,
        )
        return user

    @classmethod
    async def update(cls, user: User) -> User:
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
    async def gets(cls, user: User) -> list[User]:
        res = await cls.collection.find(
            filter={"name": {"$regex": user.name, "$options": "i"}},
            projection={"name": 1, "_id": 0, "region": 1},
        ).to_list(length=10)
        return [User.model_validate(doc) for doc in res]


class Clan_sessions(Connect):
    collection: AsyncIOMotorCollection = Connect.db["Clan"]

    @classmethod
    async def get(cls, id: int):
        res = await cls.collection.find_one(filter={"clan_id": id})
        return res


class Tank_DB(Connect):
    collection: AsyncIOMotorCollection = Connect.db["Tank"]

    @classmethod
    async def get_by_id(cls, id: int | Tank) -> dict:
        if isinstance(id, Tank):
            id = Tank.tank_id
        res = await cls.collection.find_one(filter={"tank_id": id})
        if res is not None:
            del res["_id"]
        else:
            res = {"tier": "undefined", "name": "undefined"}
        return res

    @classmethod
    async def add(cls, tank: dict | list[dict]) -> Tank:
        cls.collection.replace_one(filter={"tank_id": tank["tank_id"]})
