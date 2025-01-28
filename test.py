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


def main():
    data = asyncio.run(load_data())
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    s = datetime.now() - timedelta(days=7)
    print(s)
    s = datetime.now().timestamp() - (
        datetime.now().timestamp() - timedelta(days=1).total_seconds()
    )
    print(s)
