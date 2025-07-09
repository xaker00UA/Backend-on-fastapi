from datetime import datetime
from pydantic import BaseModel

from utils.models.response_model import Images, RestUserDB


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


class CreateTank(BaseModel):
    tank_id: int
    name: str
    nation: str
    tier: int
    is_premium: bool
    images: Images = Images()