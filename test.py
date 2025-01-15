import asyncio
from pymongo import MongoClient
from aiohttp import ClientSession
from utils.interfase.player import PlayerSession

client = MongoClient("mongodb://localhost:27017/")
client = client.test_db
session = client["Session"]
remote = MongoClient("mongodb://54.234.203.209:27017/")
remote = remote.wotblitz
remote_session = remote["Session"]


def load_name() -> list[str]:
    names = session.find(projection={"player_id": 1, "_id": 0})
    remote_names = remote_session.find(projection={"player_id": 1, "_id": 0})
    set_names = set(i.get("player_id") for i in names)
    set_remote = set(i.get("player_id") for i in remote_names)
    return list(set_names - set_remote)


async def fetch(session: ClientSession, name):
    async with session.get(
        f"http://54.234.203.209/api/eu/player/get_session?name={name}"
    ) as response:
        if response.status != 200:
            print(response.status)
        res = await response.json()
        if response.status == 404:
            print(await response.json())
        if res.get("susses") == "error":
            print(res)


async def main():
    # data = load_name()
    with open("tex.txt", "r") as f:
        data = f.read().split("\n")
    async with ClientSession() as session:
        for name in data:
            await fetch(session, name)
            print(name)


# if __name__ == "__main__":


#     asyncio.run(main())
# async def main():
#     names = []
#     for name in load_name():
#         pl = PlayerSession(id=name, reg="eu")
#         await pl.get_player_info()
#         names.append(pl.user.name)
#     with open("tex.txt", "w") as f:
#         for name in names:
#             f.write(f"{name}\n")


if __name__ == "__main__":
    asyncio.run(main())
