from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException

from utils.models.response_model import Region
from utils.service.calculate_time import round_timestamp
from ...interface.clan import ClanInterface
from ...models.clan import ClanDB, RestClan, ClanTop
from ...error import *

from utils.cache.redis_cache import redis_cache

router = APIRouter(tags=["clan"])


@router.get("/{region}/clan/", response_model=RestClan)
async def get_clan_session(region: Region, name: str):
    return await ClanInterface(name=name, region=region.value).results()


@router.get("/clan/search")
async def search_clan(name: str) -> list[ClanDB]:
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
    rounded_start_day = round_timestamp(start_day)
    rounded_end_day = round_timestamp(end_day)

    cache_key_params = {
        "limit": limit,
        "end_day": rounded_end_day,
        "start_day": rounded_start_day,
    }

    return await redis_cache.cache_or_compute(
        namespace="top_players",
        expire=6 * 3600,
        compute_func=lambda: ClanInterface.get_top_list_clan(
            limit=limit,
            end_day=end_day,
            start_day=start_day,
        ),
        **cache_key_params,
    )


@router.get("{region}clan/period")
async def get_period_clan(
    region: Region,
    name: str,
    end_day: int,
    start_day: int,
) -> RestClan:
    return await ClanInterface(name=name, region=region.value).get_period_clan_session(
        end_day=end_day, start_day=start_day
    )
