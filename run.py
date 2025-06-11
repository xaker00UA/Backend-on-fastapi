import requests
import json
from pymongo import MongoClient
import asyncio
import aiohttp

tex_api = "https://api.wotblitz.eu/wotb/encyclopedia/vehicles/?application_id=6645d2ba41b7ded38e934bd6fdd48d05"
medal_api = "https://api.wotblitz.eu/wotb/encyclopedia/achievements/?application_id=6645d2ba41b7ded38e934bd6fdd48d05"

key = "images"
db = MongoClient("mongodb://localhost:27000/").get_database("latest")
collection = db["Medal"]


def tank():
    data = requests.get(tex_api)
    data = data.json()
    result = []
    for key, val in data["data"].items():
        result.append(
            {
                "images": val.get("images"),
                "tier": val.get("tier"),
                "tank_id": val.get("tank_id"),
                "name": val.get("name"),
                "nation": val.get("nation"),
                "is_premium": val.get("is_premium"),
            }
        )
    load(result)


def medal():
    data = requests.get(medal_api, params={"language": "ru"})
    res: dict = data.json()
    result = []
    for key, val in res["data"].items():
        if not val["options"]:
            result.append(
                {
                    "name": key,
                    "image_big": val.get("image_big"),
                    "image": val.get("image"),
                }
            )
    load(result)


async def fetch(session: aiohttp.ClientSession, **kwarg):
    res_1 = await session.get(kwarg.get("image_big"))
    res_2 = await session.get(kwarg.get("image"))
    if not res_1.status == 200:
        kwarg["image_big"] = None
    if not res_2.status == 200:
        kwarg["image"] == None
    return kwarg


async def task(items: list) -> list:
    async with aiohttp.ClientSession() as session:
        task = [fetch(session=session, **i) for i in items]
        return await asyncio.gather(*task)


def check():
    with open("data.json", "r", encoding="utf-8") as file:
        res = json.load(fp=file)

    data = asyncio.run(task(res))
    print(len(data))
    with open("new.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def load(data):
    print(len(data))
    # collection.insert_many(data)
    with open("data.json", "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    check()
