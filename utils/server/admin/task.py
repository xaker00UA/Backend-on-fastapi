from typing import Awaitable, Callable

from utils.interface.clan import ClanInterface
from utils.interface.player import PlayerSession
from utils.server.admin.schemas import Commands


COMMAND_REGISTRY: dict[Commands, Callable[..., Awaitable]] = {}


def register_command(command: Commands):
    def decorator(func: Callable[..., Awaitable]):
        COMMAND_REGISTRY[command] = func
        return func

    return decorator


@register_command(Commands.RESET)
async def task_reset(name: str, region: str):
    return await PlayerSession(name=name, reg=region).reset()


@register_command(Commands.RESET_CLAN)
async def task_reset_clan(tag: str, region: str):
    return await ClanInterface(region=region, tag=tag).reset()


@register_command(Commands.UPDATE_PLAYER_DB)
async def task_update_player_db():
    return await PlayerSession.update_player_db(_all=True)


@register_command(Commands.UPDATE_CLAN_DB)
async def task_update_clan_db():
    return await ClanInterface.update_clan_db(_all=False)


@register_command(Commands.UPDATE_CLAN_ALL_DB)
async def task_update_clan_all_db():
    return await ClanInterface.update_clan_db(_all=True)


@register_command(Commands.UPDATE_PLAYER_ALL_DB)
async def task_update_player_all_db():
    return await PlayerSession.update_player_db(_all=True)
