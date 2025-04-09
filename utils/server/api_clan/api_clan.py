from fastapi import APIRouter, HTTPException
from ...interfase.clan import ClanInterface
from ...models.clan import RestClan
from ...error import *

router = APIRouter(tags=["clan"])


@router.get("/{region}/clan/", response_model=RestClan)
async def get_clan_session(region, name):
    return await ClanInterface(name=name, region=region).results()


@router.get("/clan/search")
async def search_clan(name):
    res = await ClanInterface(name=name).get_clans()
    if res:
        return res
    raise ClanNotFound(name=name)
