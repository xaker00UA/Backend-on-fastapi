import aiohttp
from pymongo import MongoClient
import asyncio
import json
from datetime import datetime, timedelta

claster = MongoClient("mongodb://localhost:27017/")

db = claster["wotblitz"]
collection = db["Tank"]


async def load_data():
    url = "https://api.wotblitz.eu/wotb/encyclopedia/vehicles/?application_id=ccef3112e27c6158fe49486193a53a65"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            return data


async def fetch(session, sem, name):
    # /api/eu/player/get_general?name=xake_r777
    url = f"/api/eu/clan/?name={name}"
    async with sem:
        async with session.get(url) as response:
            data = await response.json()
            return data


async def parse(ids: list):
    sem = asyncio.Semaphore(10)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, sem, item.get("player_id")) for item in ids]
        data = await asyncio.gather(*tasks)
        return data


def load():
    with open("test_db.Session.json", "r") as f:
        data = json.load(f)
        return data


async def main():
    # items = load()
    # data = await parse(items)
    # with open("data.json", "w") as f:
    #     json.dump(data, f, indent=4)
    await add()


async def add():
    with open("data.json", "r") as f:
        data = json.load(f)
    data = ["NOCSU,APA,QU1CK", "OMW", "KUPKA", "BLOVE", "-V-"]
    sem = asyncio.Semaphore(10)
    async with aiohttp.ClientSession(base_url="http://localhost/") as session:
        tasks = [fetch(session, sem, item) for item in data]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
