from enum import Enum
from functools import wraps
import hashlib
from time import time
from collections import OrderedDict

from fastapi import APIRouter, Depends, Request, BackgroundTasks, logger
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.datastructures import URL

from ..api_socket import player_router_socket
from ..auth import require_authentication
from ...api.wotb import APIServer
from ...interfase.player import PlayerSession
from ...models import User, RestPlayer, PlayerGeneral, PlayerDetails
from ...error import PlayerNotFound, NotFoundPlayerDB


def cache_method(ttl=60, max_cache_size=100):
    def cache_wrapper(method):
        # Use OrderedDict for cache
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

            # Remove expired data from cache
            # Instead of reassigning cache, update it in place
            expired_keys = [k for k, v in cache.items() if v["ttl"] <= current_time]
            for k in expired_keys:
                cache.pop(k)

            if key in cache and cache[key]["ttl"] > current_time:
                return cache[key]["result"]

            # Call the method and cache the result
            result = await method(self, *args, **kwargs)

            # Add to the cache
            cache[key] = {"result": result, "ttl": current_time + ttl}

            # If the cache exceeds the max size, remove the oldest items
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


class PlayerController:
    def __init__(self):
        self.router = APIRouter(tags=["player"])
        self.utils = PlayerSession
        self._setup_routes()

    def _setup_routes(self):
        self.router.add_api_route("/player", self.player, methods=["GET"])
        self.router.add_api_route(
            "/{region}/{nickname}", self.player_id, methods=["GET"]
        )
        self.router.add_api_route(
            "/search",
            self.search,
            methods=["GET"],
            responses={
                200: {
                    "susses": "ok|error",
                    "users": [{"name": "name", "region": "region"}],
                },
            },
        )
        self.router.add_api_route("/reset", self.reset, methods=["GET"])

    @require_authentication
    async def player(self, request: Request):
        token = request.cookies.get("access_token")
        player = self.utils(access_token=token)
        await player.get_player_DB()
        user = player.old_user
        reg, name = user.region, user.name
        return JSONResponse({"susses": "ok", "region": reg, "nickname": name})

    async def player_id(self, nickname: str, region: RegionEnum, request: Request):
        return RedirectResponse(
            URL(f"player/get_general?name={nickname}"), status_code=301
        )

    @require_authentication
    async def reset(self, request: Request):
        token = request.cookies.get("access_token")
        player = self.utils(access_token=token)
        await player.reset()
        return RedirectResponse("/player")

    async def search(self, player_name):
        res = await PlayerSession(name=player_name).get_players()
        if res:
            return {"susses": "ok", "users": res}
        return {"susses": "error"}


class PlayerStats:
    def __init__(self):
        self.router = APIRouter(prefix="/{region}/player", tags=["stats"])
        self.utils = PlayerSession
        self._setup_routes()

    def _setup_routes(self):
        # self.router.add_api_route("/get_rating", self.get_rating, methods=["GET"])
        self.router.add_api_route(
            "/get_general",
            self.get_general,
            methods=["GET"],
            responses={
                200: {
                    "description": "Успешный ответ",
                    "content": {
                        "application/json": {
                            "example": {
                                "error": {"success": "error", "message": "string"},
                                "ok": {
                                    "success": "ok",
                                    "player": {
                                        "nickname": "name",
                                        "general": User.model_json_schema(),  # Если User - это объект, замените его на пример данных
                                    },
                                },
                            }
                        }
                    },
                }
            },
        )
        self.router.add_api_route("/get_session", self.get_session, methods=["GET"])

    async def get_rating(self):
        pass

    @cache_method()
    async def get_general(self, region, name):
        try:
            data = await self.utils(name=name, reg=region).get_player_info()

        except PlayerNotFound:
            return {"susses": "error", "message": "Player not found"}
        return {
            "success": "ok",
            "player": {"nickname": data.name, "general": data.acount.result()},
        }

    @cache_method()
    async def get_session(self, name, region, background_tasks: BackgroundTasks):
        try:
            data = await self.utils(name=name, reg=region).results()
        except NotFoundPlayerDB:
            background_tasks.add_task(self.utils(name=name, reg=region).add_player)
            return {"susses": "error", "message": "Player add db"}
        except PlayerNotFound:
            return {"susses": "error", "message": "Player not found"}
        except Exception as e:
            return {"susses": "error", "message": str(e)}
        return {"susses": "ok", "session": data[0], "update": data[1], "now": data[2]}


router = PlayerController().router
stats = PlayerStats().router
stats.include_router(router=player_router_socket, tags=["WebSocket"])
