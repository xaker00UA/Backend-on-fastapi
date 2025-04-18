from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from ...interfase.clan import ClanInterface
from ...models.clan import RestClan, ClanTop
from ...error import *

router = APIRouter(tags=["clan"])


@router.get("/{region}/clan/", response_model=RestClan)
async def get_clan_session(region, name):
    return await ClanInterface(name=name, region=region).results()


@router.get("/clan/search")
async def search_clan(name):
    res = await ClanInterface(name=name).get_clans()
    if res:
        return res
    raise ClanNotFound(name=name)


@router.get("/top_clan")
async def top_clan_list(
    end_day: float = datetime.now().replace(microsecond=0).timestamp(),
    start_day: float = (datetime.now() - timedelta(days=7))
    .replace(microsecond=0)
    .timestamp(),
    limit: int = 10,
) -> list[ClanTop]:
    return await ClanInterface.get_top_list_clan(
        end_day=end_day, start_day=start_day, limit=limit
    )
