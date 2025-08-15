from typing import Awaitable, Callable

from utils.interface.clan import ClanInterface
from utils.interface.player import PlayerSession
from utils.interface.task import TaskInterface
from utils.server.admin.schemas import Commands
import asyncio

COMMAND_REGISTRY: dict[Commands, Callable[..., Awaitable]] = {}


def register_command(command: Commands):
    def decorator(func: Callable[..., Awaitable]):
        COMMAND_REGISTRY[command] = func
        return func

    return decorator


async def _update_db(entity_cls_or_method, *, _all=True, use_task=False, flag=None):
    if use_task:
        interface = TaskInterface()
        task = await interface.create_task(flag=flag)
        asyncio.create_task(entity_cls_or_method(task.id, _all=_all))
        return task
    return await entity_cls_or_method(_all=_all)


async def _reset_entity(entity_cls, **kwargs):
    return await entity_cls(**kwargs).reset()


@register_command(Commands.RESET)
async def task_reset(name: str, region: str):
    return await TaskInterface().reset(flag="player", name=name, reg=region)


@register_command(Commands.RESET_CLAN)
async def task_reset_clan(tag: str, region: str):
    return await TaskInterface().reset(flag="clan", tag=tag, region=region)


@register_command(Commands.UPDATE_PLAYER_DB)
async def task_update_player_db():
    return await _update_db(
        TaskInterface().update_player_db, _all=False, use_task=True, flag="player"
    )


@register_command(Commands.UPDATE_CLAN_DB)
async def task_update_clan_db():
    return await _update_db(
        TaskInterface().update_clan_db, _all=False, use_task=True, flag="clan"
    )


@register_command(Commands.UPDATE_CLAN_ALL_DB)
async def task_update_clan_all_db():
    return await _update_db(
        TaskInterface().update_clan_db, _all=True, use_task=True, flag="clan"
    )


@register_command(Commands.UPDATE_PLAYER_ALL_DB)
async def task_update_player_all_db():
    return await _update_db(
        TaskInterface().update_player_db, _all=True, use_task=True, flag="player"
    )
