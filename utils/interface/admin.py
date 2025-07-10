import os
import time
from datetime import datetime
from prometheus_client import REGISTRY
import re
from utils.database.Mongo import Clan_sessions, Player_sessions
from utils.database.admin import get_active_users
from utils.models.base_models import Singleton
from utils.server.admin.schemas import CreateTank
from utils.settings.logger import LoggerFactory
from datetime import datetime
from utils.database.Mongo import Tank_DB


class MetricsInterface(Singleton):
    def __init__(self, time):

        self.app_start_time = time
        self.clan = Clan_sessions
        self.player = Player_sessions

    def get_counter_value(self, name: str, labels: str | None = None):
        for metric in REGISTRY.collect():
            if metric.name == name:
                for sample in metric.samples:
                    if labels is not None:
                        match = re.search(labels, sample.labels.get("path"))
                        if match:
                            return sample.value
                    else:
                        return sample.value
        return 0

    async def get_uptime(self):
        return int(time.time() - self.app_start_time)

    async def get_user_count(self):
        return await self.player.collection.count_documents({})

    async def get_clan_count(self):
        return await self.clan.collection.count_documents({})

    async def get_last_clan_update(self):
        result = await self.player.collection.find_one(
            sort=[("timestamp", -1)], projection={"timestamp": 1}
        )
        return datetime.fromtimestamp(result["timestamp"]) if result else None

    async def get_last_player_update(self):
        result = await self.clan.collection.find_one(
            sort=[("timestamp", -1)], projection={"timestamp": 1}
        )
        return datetime.fromtimestamp(result["timestamp"]) if result else None

    async def get_active_users_14d(self):
        data = get_active_users()
        return [
            {"name": i.name, "player_id": i.player_id, "region": i.region} for i in data
        ]

    async def get_last_logs(self, limit=100):
        return LoggerFactory.head_log(limit)

    async def get_custom_api_call_count(
        self,
    ):
        data = {
            "/get_session": self.get_counter_value("http_requests", "get_session$"),
            "/reset": self.get_counter_value("http_requests", "reset$"),
            "/clan_session": self.get_counter_value("http_requests", "clan$"),
        }
        return data

    async def get_external_api_calls(self):
        return self.get_counter_value("external_api_requests")

    async def collect_all(self, limit):
        data = await self.get_active_users_14d()
        return {
            "uptime_seconds": await self.get_uptime(),
            "user_count": await self.get_user_count(),
            "clan_count": await self.get_clan_count(),
            "last_players_update": await self.get_last_player_update(),
            "last_clan_update": await self.get_last_clan_update(),
            "count_active_users": len(data),
            "active_users_list": data,
            "external_api_calls": await self.get_external_api_calls(),
            "custom_api_calls": await self.get_custom_api_call_count(),
            "last_1000_logs": await self.get_last_logs(limit),
        }


class AdminInterface:
    def __init__(self):
        self.MEDIA_DIR = "media"
        if not os.path.exists(self.MEDIA_DIR):
            os.makedirs(self.MEDIA_DIR)

    async def add_tank(self, tank_data: CreateTank, image_big, image_small):
        path_big, path_small = None, None
        if image_big:
            path_big = os.path.join(self.MEDIA_DIR, f"{tank_data.tank_id}_big.png")
            image_big.filename = f"{tank_data.tank_id}_big.png"
            with open(path_big, "wb") as f:
                f.write(image_big.file.read())
        if image_small:
            path_small = os.path.join(self.MEDIA_DIR, image_small.filename)
            image_small.filename = f"{tank_data.tank_id}_small.png"
            with open(path_small, "wb") as f:
                f.write(image_small.file.read())
        tank_data.images.preview = path_small
        tank_data.images.normal = path_big
        await Tank_DB.add(tank_data.model_dump())
        return tank_data
