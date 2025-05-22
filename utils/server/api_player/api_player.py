import asyncio
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
from ...models.respnse_model import Parameter, Region, RestUser, RestUserDB, TopPlayer
from ...error import NotFoundPlayerDB


router = APIRouter(tags=["player"])


@router.get("/player")
async def player(token=Depends(require_authentication)) -> RestUserDB:
    player = PlayerSession(access_token=token)
    await player.get_player_DB()
    user = RestUserDB.model_validate(player.old_user, from_attributes=True)
    return user


@router.get("/reset")
async def reset(
    background_tasks: BackgroundTasks, token=Depends(require_authentication)
) -> bool:
    player = PlayerSession(access_token=token)
    background_tasks.add_task(player.reset)
    return True


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
) -> list[TopPlayer]:
    return await PlayerSession.top_players(
        limit=limit, parameter=parameter, start_day=start_day
    )


stats = APIRouter(prefix="/{region}/player", tags=["stats"])


@stats.get("/get_general", response_model=RestUser)
async def get_general(
    region: Region, name: str, access_token: str = Cookie("access_token")
):
    data = await PlayerSession(
        name=name, reg=region.value, access_token=access_token
    ).get_player_info()
    return data.result("now")


@stats.get("/get_session", response_model=RestUser)
async def get_session(
    region: Region, name: str, background_tasks: BackgroundTasks
) -> RestUser:
    try:
        return await PlayerSession(name=name, reg=region.value).results()
    except NotFoundPlayerDB:
        # await PlayerSession(name=name, reg=region.value).add_player()
        # background_tasks.add_task()
        asyncio.create_task(PlayerSession(name=name, reg=region.value).add_player())
        # return
        raise NotFoundPlayerDB(region=region.value, name=name)


@stats.get("/period")
async def get_period(region: Region, name: str, start_day: int, end_day: int):
    return await PlayerSession(name=name, reg=region.value).get_period(
        start_day, end_day
    )


stats.include_router(router=player_router_socket, tags=["WebSocket"])
