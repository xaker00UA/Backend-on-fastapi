from pydantic import BaseModel
from redis import asyncio as aioredis
import json
import hashlib
from typing import Any, Callable, Optional
from utils.settings.config import EnvConfig

from loguru import logger


class RedisCache:
    def __init__(self, redis_url: str = EnvConfig.REDIS):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        if not self.redis:
            self.redis = await aioredis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            await self.redis.select(0 if EnvConfig.NAME_DB == "wotblitz" else 1)

    async def get(self, key: str) -> Any:
        await self.connect()
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def set(self, key: str, value: str, expire: int = 3600):
        await self.connect()
        await self.redis.set(key, value, ex=expire)

    def make_key(self, namespace: str, **params) -> str:
        raw = json.dumps(params, sort_keys=True)
        hash_key = hashlib.md5(raw.encode()).hexdigest()
        return f"{namespace}:{hash_key}"

    async def cache_or_compute(
        self, namespace: str, expire: int, compute_func: Callable, **params
    ) -> Any:
        key = self.make_key(namespace, **params)
        cached = await self.get(key)
        if cached:
            logger.bind(name="root").info(f"Взято из кеша функция {key}")
            return cached
        model = await compute_func()
        if isinstance(model, list):
            result = [i.model_dump() for i in model]
            result = json.dumps(result)
        if isinstance(model, BaseModel):
            result = model.model_dump_json()
        await self.set(key, result, expire)
        return model


redis_cache = RedisCache()
