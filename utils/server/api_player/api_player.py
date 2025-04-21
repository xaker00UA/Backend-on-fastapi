from datetime import datetime, timedelta
from functools import wraps
import hashlib
from time import time
from collections import OrderedDict

from fastapi import (
    APIRouter,
    Cookie,
    BackgroundTasks,
    Depends,
)
from fastapi.responses import JSONResponse

from ..api_socket import player_router_socket
from ..auth import require_authentication

from ...interfase.player import PlayerSession
from ...models.respnse_model import Parameter, Region, RestUser, RestUserDB
from ...error import NotFoundPlayerDB


def cache_method(ttl=60, max_cache_size=100):
    def cache_wrapper(method):
        cache = OrderedDict()

        @wraps(method)
        async def wrapper(self, *args, **kwargs):
            kwargs_filtered = {
                key: value
                for key, value in kwargs.items()
                if not isinstance(value, BackgroundTasks)
            }
            key = hashlib.md5(f"{args}{kwargs_filtered}".encode()).hexdigest()
            current_time = round(time())
            expired_keys = [k for k, v in cache.items() if v["ttl"] <= current_time]
            for k in expired_keys:
                cache.pop(k)
            if key in cache and cache[key]["ttl"] > current_time:
                return cache[key]["result"]

            result = await method(self, *args, **kwargs)

            cache[key] = {"result": result, "ttl": current_time + ttl}
            if len(cache) > max_cache_size:
                cache.popitem(last=False)  # Remove the oldest item
            return result

        return wrapper

    return cache_wrapper


router = APIRouter(tags=["player"])


@router.get("/player")
async def player(token=Depends(require_authentication)):
    player = PlayerSession(access_token=token)
    await player.get_player_DB()
    user = player.old_user
    reg, name = user.region, user.name
    return JSONResponse({"region": reg, "nickname": name})


@router.get("/reset")
async def reset(
    background_tasks: BackgroundTasks, token=Depends(require_authentication)
):
    player = PlayerSession(access_token=token)
    background_tasks.add_task(player.reset)
    return JSONResponse({"susses": "ok"})


@router.get("/search")
async def search(name: str) -> list[RestUserDB]:
    res = await PlayerSession(name=name).get_players()
    if res:
        return res
    raise NotFoundPlayerDB(name=name)


@router.get(
    "/top_players",
)
async def top_players(
    limit: int = 10,
    parameter: Parameter = Parameter.battles,
    start_day: int = int(
        datetime.now().timestamp() - timedelta(days=7).total_seconds()
    ),
):
    return await PlayerSession.top_players(
        limit=limit, parameter=parameter, start_day=start_day
    )


stats = APIRouter(prefix="/{region}/player", tags=["stats"])


@cache_method
@stats.get("/get_general", response_model=RestUser)
async def get_general(
    region: Region, name: str, access_token: str = Cookie("access_token")
):
    data = await PlayerSession(
        name=name, reg=region.value, access_token=access_token
    ).get_player_info()
    return data.result("now")


@cache_method
@stats.get("/get_session", response_model=RestUser)
async def get_session(
    region: Region, name: str, background_tasks: BackgroundTasks
) -> RestUser:
    try:
        return await PlayerSession(name=name, reg=region.value).results()
    except NotFoundPlayerDB:
        background_tasks.add_task(PlayerSession(name=name, reg=region.value).add_player)
        raise NotFoundPlayerDB(region=region.value, name=name)


@cache_method
@stats.get("/period")
async def get_period(region: Region, name: str, start_day: int, end_day: int):
    return await PlayerSession(name=name, reg=region.value).get_period(
        start_day, end_day
    )


stats.include_router(router=player_router_socket, tags=["WebSocket"])
