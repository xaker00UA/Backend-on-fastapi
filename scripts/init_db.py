from ast import parse
import asyncio
from aiohttp import ClientSession
from pydantic import BaseModel, Field

from utils.settings.config import Config, EnvConfig
from utils.database.Mongo import Tank_DB, Medal_DB


class Image(BaseModel):
    preview: str | None = None
    normal: str | None = None


class Tank(BaseModel):
    images: Image
    tier: int
    tank_id: int
    name: str
    nation: str
    is_premium: bool


class Medal(BaseModel):
    name: str
    image: str


async def fetch(url, session: ClientSession):
    async with session.get(url) as response:
        return await response.json()


def parse_response(tanks: dict, medal: dict):
    parse_tank = []
    parse_medal = []
    for item, val in tanks["data"].items():
        parse_tank.append(Tank.model_validate(val))

    for item, val in medal["data"].items():
        val["name"] = item
        if val["options"]:
            for i in val["options"]:
                parse_medal.append(Medal.model_validate(i))
        else:
            parse_medal.append(Medal.model_validate(val))

    return parse_tank, parse_medal


async def dump_db(tank, medal):
    for item in tank:
        await Tank_DB.add(item.model_dump())
    for item in medal:
        await Medal_DB.add(item.model_dump())


async def main():
    task = []
    async with ClientSession() as session:
        template_medal = Config().get().game_api.urls.get_tankopedia_achievements
        template_tank = Config().get().game_api.urls.get_tankopedia_tank
        tank = template_tank.replace("<app_id>", EnvConfig.WG_APP_IDS)
        medal = template_medal.replace("<app_id>", EnvConfig.WG_APP_IDS)

        task.append(fetch(tank, session))
        task.append(fetch(medal, session))
        res = await asyncio.gather(*task)
        tank, medal = parse_response(res[0], res[1])
        await dump_db(tank, medal)


if __name__ == "__main__":
    asyncio.run(main())
