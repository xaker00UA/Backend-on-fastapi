from datetime import datetime
from enum import Enum
from typing import Callable
from pydantic import BaseModel, PrivateAttr, model_validator

from utils.models.response_model import Images, Region, RestUserDB


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


class Commands(str, Enum):
    RESET = "reset_user"
    RESET_CLAN = "reset_clan"
    DELETE = "delete_user"
    DELETE_CLAN = "delete_clan"
    UPDATE_PLAYER_DB = "update_player_db"
    UPDATE_CLAN_DB = "update_clan_db"
    UPDATE_PLAYER_ALL_DB = "update_player_all_db"
    UPDATE_CLAN_ALL_DB = "update_clan_all_db"


class ResetPlayerArgs(BaseModel):
    name: str
    region: str


class ResetClanArgs(BaseModel):
    tag: str
    region: str


class EmptyArgs(BaseModel):
    pass


COMMAND_ARGS: dict[Commands, type[BaseModel]] = {
    Commands.RESET: ResetPlayerArgs,
    Commands.RESET_CLAN: ResetClanArgs,
    Commands.UPDATE_PLAYER_DB: EmptyArgs,
    Commands.UPDATE_CLAN_DB: EmptyArgs,
    Commands.UPDATE_PLAYER_ALL_DB: EmptyArgs,
    Commands.UPDATE_CLAN_ALL_DB: EmptyArgs,
}


class CommandRequest(BaseModel):
    command: Commands
    arguments: dict = {}

    _task: Callable | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def resolve(self):
        from utils.server.admin.task import COMMAND_REGISTRY

        args_model_cls = COMMAND_ARGS.get(self.command)
        if not args_model_cls:
            raise ValueError(f"No args schema for command {self.command}")

        # ✅ Автовалидация аргументов
        validated_args = args_model_cls(**self.arguments)

        handler = COMMAND_REGISTRY[self.command]
        self._task = lambda: handler(**validated_args.model_dump())
        return self

    async def run(self):
        if self._task:
            return await self._task()
        AttributeError("Command not found")
