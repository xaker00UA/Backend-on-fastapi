from datetime import datetime
from pydantic import BaseModel

from utils.models.response_model import RestUserDB


class AdminStats(BaseModel):
    uptime_seconds: int
    user_count: int
    clan_count: int
    last_players_update: datetime
    last_clan_update: datetime
    count_active_users: int
    active_users_list: list[RestUserDB]
    external_api_calls: int
    custom_api_calls: dict[str, int]
    last_1000_logs: list[dict]
