from enum import Enum
from functools import wraps
import hashlib
from time import time
from collections import OrderedDict

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, logger, Depends
from fastapi.responses import RedirectResponse, JSONResponse

from utils.error.exception import BaseCustomException

from ..api_socket import player_router_socket
from ..auth import require_authentication

from ...interfase.player import PlayerSession
from ...models.respnse_model import RestUser
from ...error import NotFoundPlayerDB
import logging

logger = logging.getLogger()


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


class RegionEnum(str, Enum):
    eu = "eu"
    asia = "asia"
    com = "com"
    na = "na"


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
async def search(player_name):
    res = await PlayerSession(name=player_name).get_players()
    if res:
        return res
    raise HTTPException(status_code=404, detail="Player not found")


stats = APIRouter(prefix="/{region}/player", tags=["stats"])


@cache_method
@stats.get("/get_general", response_model=RestUser)
async def get_general(region, name):
    try:
        data = await PlayerSession(name=name, reg=region).get_player_info()
        return data.result("now")
    except BaseCustomException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500)


@cache_method
@stats.get("/get_session", response_model=RestUser)
async def get_session(region, name, background_tasks: BackgroundTasks) -> RestUser:
    try:
        return await PlayerSession(name=name, reg=region).results()
    except NotFoundPlayerDB:
        background_tasks.add_task(PlayerSession(name=name, reg=region).add_player)
        return {"susses": "error", "message": "Player add db"}
    except BaseCustomException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500)


stats.include_router(router=player_router_socket, tags=["WebSocket"])
