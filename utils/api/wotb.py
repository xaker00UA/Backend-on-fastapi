from aiohttp import ClientSession, ClientResponse
from asynciolimiter import Limiter
import asyncio
import time

from utils.models import PlayerGeneral, User, Singleton, PlayerDetails
from utils.api.cache import Cache
from utils.error.exception import *
from utils.settings.config import Config, EnvConfig
from utils.error.exception import PlayerNotFound
import atexit

LIMIT = 10
Count = 1


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
            global Count

            print(
                f"Count={Count} Function {func.__name__} took {end_time - start_time} seconds to execute"
            )
            Count += 1

    return wrapper


class APIServer(Singleton):

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.limiter = Limiter(LIMIT)
            self.session = ClientSession()
            self._session = self.session
            self._players_stats = []
            self.exact = True
            self.cache = Cache()
            self._config = Config().get()
            self.player_stats = {}
            self.player = {}

            self.initialized = True
            atexit.register(self.close)

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

    async def parse_response(
        self, response: ClientResponse, count: bool = True, status_response: bool = True
    ) -> dict:
        data = await response.json()
        status = response.status
        match status:
            case status if 200 <= status < 300:
                pass
            case status if 300 <= status < 400:
                raise Exception("Redirect")
            case status if 400 <= status < 500:
                raise RequestError("Not found")
            case status if 500 <= status:
                raise Exception("Server error")
            case _:
                raise Exception(f"Unknown error status {status}")
        if status_response:
            if data["status"] != "ok":
                raise RequestError(
                    f"{data["error"]['message']}",
                )
        if count:
            if data["meta"]["count"] == 0:
                raise PlayerNotFound(
                    f"Игрок {response.url.query.get('search')} не найден"
                )
        return data

    @timer
    async def fetch(self, url, parser=True):
        await self.limiter.wait()
        async with self.session.get(url) as response:
            if parser:
                return await self.parse_response(response)
            else:
                return await response.json()

    async def get_user_id(self, user: User) -> tuple[int, str]:
        player_id = user.player_id
        reg = user.region
        if not player_id:
            name = user.name
            player = self.cache.get(name)
            if not player:
                player_id = await self.get_id(reg, name)
            else:
                player_id = player.player_id
        return player_id, reg

    async def create_task(self):
        pass

    async def get_player_stats(self):
        pass

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
        user = User(region=region, name=nickname, player_id=player_id)

        self.cache.set(nickname, user)
        return player_id

    async def get_general(self, user: User) -> User:
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
        # rating = await self.get_raring(user)
        data = data["data"][str(player_id)]
        # data["statistics"]["rating"].update(rating)
        general = PlayerGeneral(**data)
        res = User(
            region=reg,
            player_id=player_id,
            acount=general,
            name=user.name,
            access_token=token,
        )
        return res

    async def get_details_tank(self, user: User) -> User:
        player_id, reg = await self.get_user_id(user)
        token = user.access_token

        url_template = self._config.game_api.urls.get_tank_stats
        url = (
            url_template.replace("<reg_url>", self._get_url_by_reg(reg))
            .replace("<app_id>", self._get_id_by_reg(reg))
            .replace("<player_id>", str(player_id))
            .replace("<access_token>", str(token if token else ""))
        )
        data, gen, rating = await asyncio.gather(
            self.fetch(url), self.get_general(user), self.get_rating(user)
        )
        data["tanks"] = data["data"][str(player_id)]
        gen = gen.model_copy(update={"account": {"statistics": {"rating": rating}}})
        res = User(
            region=reg,
            player_id=player_id,
            name=user.name,
            access_token=token,
            acount=PlayerDetails(**data, general=gen.acount),
        )
        return res

    async def get_medal(self, user):
        player_id, reg = await self.get_user_id(user)

        url_template = self._config.game_api.urls.get_achievements
        url = (
            url_template.replace("<reg_url>", self._get_url_by_reg(reg))
            .replace("<app_id>", self._get_id_by_reg(reg))
            .replace("<player_id>", str(player_id))
        )
        data = await self.fetch(url)
        print(data)
        # FIXME: надо чтобы возрщало модель медалей и не было ошибки при большем количестве
        # FIXME: параметров желетально чтобы даже изменяло модель на основе самого
        # FIXME: большого количества параметров

    async def get_token(self, reg="eu") -> str:
        reg = self._get_url_by_reg(reg)
        url_template = self._config.game_api.urls.get_token
        url = url_template.replace("<reg_url>", reg).replace(
            "<app_id>", self._get_id_by_reg(reg)
        )
        data = await self.fetch(url)
        data = data["data"]["location"]
        return data

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
        data = await self.fetch(url, parser=False)
        if data.get("neighbors"):
            score = data["neighbors"][0]["score"]
            number = data["neighbors"][0]["number"]
        else:
            score = 0
            number = 0
        return {"score": score, "number": number}

    async def get_clan_id(self):
        # TODO: реализовать функцию для клан айди
        pass

    async def get_members(self):
        # TODO: реализовать функцию для получения игроков
        pass

    async def get_tank_api(self):
        # TODO: реализовать функцию для получения информации о танках
        # важно чтобы обновляло сущестующую бд а не заменяло ее так как не все даные есть в этом апи
        pass

    def close(self):
        asyncio.run(self.session.close())
