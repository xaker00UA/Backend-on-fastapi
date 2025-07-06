import json
from aiohttp import ClientSession, ClientResponse
from asynciolimiter import Limiter
from prometheus_client import Counter
import asyncio
import time
from utils.cache.redis_cache import RedisCache
from utils.models.base_models import Singleton
from utils.models.player import UserDB, PlayerDetails
from utils.models.clan import Clan, ClanDetails
from utils.error.exception import *
from utils.models.tank import PlayerModel
from utils.settings.config import Config, EnvConfig
from utils.error.exception import PlayerNotFound

from ..settings.logger import LoggerFactory


def timer(func):
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        except:
            raise
        finally:
            end_time = time.time()
            LoggerFactory.log(
                f"Function {func.__name__} took {end_time - start_time} seconds to execute",
                level="DEBUG",
                channel="api",
            )

    return wrapper


class APIServer(Singleton):

    def __init__(self):
        if not hasattr(self, "initialized"):
            self._config = Config().get()
            self.limiter = Limiter(EnvConfig.LIMIT)
            self.session = None
            self._session = self.session
            self.exact = True
            self.redis_cache = RedisCache()
            self.player_stats = {}
            self.player = {}
            self.initialized = True
            self.external_api_counter = Counter(
                "external_api_requests",
                "Total requests to external APIs",
            )

    async def init_session(self):
        if self.session is None:
            self.session = ClientSession()
            self._session = self.session

    def _get_url_by_reg(self, reg: str):
        match reg.lower():
            case "eu":
                return self._config.game_api.reg_urls.eu
            case "asia" | "as":
                return self._config.game_api.reg_urls.asia
            case "com" | "na":
                return self._config.game_api.reg_urls.na
            case _:
                raise TypeError()

    def _get_id_by_reg(self, reg: str):
        reg = reg.lower()
        if reg in {"eu", "com", "asia", "na", "as"}:
            tok = EnvConfig.WG_APP_IDS
            return tok
        raise TypeError()

    async def parse_status(self, response: ClientResponse):
        status = response.status
        match status:
            case status if 200 <= status < 300:
                pass
            case status if 300 <= status < 400:
                raise Exception("Redirect")
            case status if 400 <= status < 500:
                raise RequestError("Not found")
            case 504:
                raise ServerIsTemporarilyUnavailable()
            case status if 500 <= status:
                raise Exception("Server error")
            case _:
                raise Exception(f"Unknown error status {status}")

    async def parse_response(
        self, response: ClientResponse, count: bool = True, status_response: bool = True
    ) -> dict:
        data = await response.json()

        if status_response:
            if data["status"] != "ok":
                message = data["error"]["message"]
                value = data["error"].get("value")
                match message:
                    case "INVALID_ACCESS_TOKEN":
                        raise InvalidAccessToken(value=value)
                    case "INVALID_IP_ADDRESS":
                        raise InvalidIpAddress(value=value)
                    case "REQUEST_LIMIT_EXCEEDED":
                        raise RequestLimitExceeded(value)
                    case "APPLICATION_IS_BLOCKED":
                        raise ApplicationIsBlocked(value)
                    case "SOURCE_NOT_AVAILABLE":
                        raise ServerIsTemporarilyUnavailable
                    case _:
                        raise RequestError(message=message, value=value)
        if count:
            if data["meta"]["count"] == 0:
                raise PlayerNotFound(
                    f"Игрок {response.url.query.get('search')} не найден"
                )
        return data

    @timer
    async def fetch(self, url, parser=True):
        await self.limiter.wait()
        self.external_api_counter.inc()
        LoggerFactory.log(
            f"url={url}",
            level="DEBUG",
            channel="api",
        )
        async with self.session.get(url) as response:
            await self.parse_status(response)
            if parser:
                return await self.parse_response(response)
            else:
                return await response.json()

    async def fetch_post(self, url, body):
        await self.limiter.wait()
        self.external_api_counter.inc()
        LoggerFactory.log(
            f"url={url}",
            level="DEBUG",
            channel="api",
        )
        async with self.session.post(url, json=body) as response:
            await self.parse_status(response)
            return await response.json()

    async def get_user_id(self, user: UserDB) -> tuple[int, str]:
        player_id = user.player_id
        reg = user.region
        if not player_id:
            name = user.name
            player = await self.redis_cache.get(name)
            if not player:
                player_id = await self.get_id(reg, name)
            else:
                # player = json.loads(player)
                player = UserDB(
                    player_id=player.get("player_id"),
                    region=player.get("region"),
                    name=player.get("name"),
                )
                player_id = player.player_id
        return player_id, reg

    async def get_id(self, region, nickname):
        reg_url = self._get_url_by_reg(region)
        types = "exact" if self.exact else "startswith"
        app_id = self._get_id_by_reg(region)
        if not reg_url:
            raise ValueError(f"Некорректный регион: {region}")

        url_template = self._config.game_api.urls.get_id
        url = (
            url_template.replace("<reg_url>", reg_url)
            .replace("<app_id>", app_id)
            .replace("<nickname>", nickname)
            .replace("<search_type>", types)
        )
        data = await self.fetch(url)
        player_id = int(data["data"][0]["account_id"])
        user = UserDB(region=region, name=nickname, player_id=player_id)
        await self.redis_cache.set(nickname, user.model_dump_json())
        return player_id

    async def get_general(self, user: UserDB) -> UserDB:
        player_id, reg = await self.get_user_id(user)
        token = user.access_token

        url_template = self._config.game_api.urls.get_stats
        url = (
            url_template.replace("<reg_url>", self._get_url_by_reg(reg))
            .replace("<app_id>", self._get_id_by_reg(reg))
            .replace("<player_id>", str(player_id))
            .replace("<access_token>", str(token if token else ""))
        )
        data = await self.fetch(url)
        if data and data["data"][str(player_id)]:
            data = data["data"][str(player_id)]
            general = PlayerModel(**data)
            res = UserDB(
                region=reg,
                player_id=player_id,
                acount=general,
                name=data["nickname"],
                access_token=token,
            )
            return res
        else:
            raise NoUpdatePlayer(user=user)

    async def get_details_tank(self, user: UserDB, rating=True) -> UserDB:
        player_id, reg = await self.get_user_id(user)
        token = user.access_token

        url_template = self._config.game_api.urls.get_tank_stats
        url = (
            url_template.replace("<reg_url>", self._get_url_by_reg(reg))
            .replace("<app_id>", self._get_id_by_reg(reg))
            .replace("<player_id>", str(player_id))
            .replace("<access_token>", str(token if token else ""))
        )

        tasks = [
            asyncio.create_task(self.fetch(url), name="fetch"),
            asyncio.create_task(self.get_general(user), name="get_general"),
        ]
        if rating:
            tasks.append(asyncio.create_task(self.get_rating(user), name="get_rating"))
        done, pending = await asyncio.wait(tasks, timeout=200)
        results = {}
        for task in done:
            results[task.get_name()] = task.result()

        for task in pending:
            results[task.get_name()] = None
            task.cancel()
        data = results.get("fetch")

        if data["data"][str(player_id)] is None:
            raise NoUpdatePlayer(user=user)

        data["tanks"] = data["data"][str(player_id)]
        gen = results.get("get_general")
        rat = results.get("get_rating")
        if rat:
            gen = gen.model_copy(
                update={
                    "acount": gen.acount.model_copy(
                        update={
                            "statistics": gen.acount.statistics.model_copy(
                                update={
                                    "rating": gen.acount.statistics.rating.model_copy(
                                        update=rat
                                    )
                                }
                            )
                        }
                    )
                }
            )

        res = UserDB(
            region=reg,
            player_id=player_id,
            name=gen.name,
            access_token=token,
            acount=PlayerDetails(**data, **gen.acount.model_dump()),
        )
        return res

    async def get_medal(self, user) -> dict:
        player_id, reg = await self.get_user_id(user)

        url_template = self._config.game_api.urls.get_achievements
        url = (
            url_template.replace("<reg_url>", self._get_url_by_reg(reg))
            .replace("<app_id>", self._get_id_by_reg(reg))
            .replace("<player_id>", str(player_id))
        )
        data = await self.fetch(url)
        return data["data"][str(player_id)]["achievements"]

    async def get_token(self, redirect_url, reg="eu") -> str:
        reg = self._get_url_by_reg(reg)
        url_template = self._config.game_api.urls.get_token
        url = (
            url_template.replace("<reg_url>", reg)
            .replace("<app_id>", self._get_id_by_reg(reg))
            .replace("<redirect_url>", redirect_url)
        )
        data = await self.fetch(url)
        data = data["data"]["location"]
        return data

    async def longer_token(self, user: UserDB):
        reg = self._get_url_by_reg(user.region)
        url_template = self._config.game_api.urls.longer_token
        url = url_template.replace("<reg_url>", reg)
        body = {
            "application_id": self._get_id_by_reg(reg),
            "access_token": user.access_token,
        }
        data = await self.fetch_post(url, body=body)
        if data["status"] == "ok":
            user.access_token = data["data"]["access_token"]
            return user.access_token
        else:
            return user

    async def logout(self, req, token):
        req = self._get_url_by_reg(req)
        url_template = self._config.game_api.urls.logout
        url = url_template.replace("<reg_url>", req).replace(
            "<app_id>", self._get_id_by_reg(req).replace("<token>", token)
        )
        data = await self.fetch(url, parser=False)
        return True

    async def get_rating(self, user) -> set[int, int]:
        player_id, region = await self.get_user_id(user)
        reg = self._get_url_by_reg(region)
        url_template = self._config.game_api.urls.get_position_rating
        url = url_template.replace("<reg_url>", reg).replace(
            "<player_id>", str(player_id)
        )
        try:
            data = await self.fetch(url, parser=False)
            score = data["neighbors"][0]["score"]
            number = data["neighbors"][0]["number"]
        except Exception as e:
            score = 0
            number = 0
        return {"score": score, "number": number}

    async def get_clan_info(self, name, region) -> Clan:
        reg = self._get_url_by_reg(region)
        url_template = self._config.game_api.urls.search_clan
        url = (
            url_template.replace("<reg_url>", reg)
            .replace("<app_id>", self._get_id_by_reg(reg))
            .replace("<name>", name)
        )
        data = await self.fetch(url)
        for item in data["data"]:
            if item["name"] == name:
                return Clan(**item)
            if item["tag"] == name.upper():
                return Clan(**item)
        raise ClanNotFound(name)

    async def get_clan_details(
        self,
        region,
        name=None,
        clan_id=None,
    ):
        reg = self._get_url_by_reg(region)
        url_template = self._config.game_api.urls.get_clan_info
        url = url_template.replace("<reg_url>", reg).replace(
            "<app_id>", self._get_id_by_reg(reg)
        )
        if not clan_id:
            clan = await self.get_clan_info(name, region)
            clan_id = clan.clan_id
            url = url.replace("<clan_id>", str(clan_id))

        else:
            url = url.replace("<clan_id>", str(clan_id))
        data = await self.fetch(url)
        return ClanDetails(**data["data"][str(clan_id)])

    async def close(self):
        if self.session:
            await self.session.close()
