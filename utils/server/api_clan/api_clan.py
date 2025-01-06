from fastapi import APIRouter, HTTPException
from ...interfase.clan import ClanInterface
from ...models.clan import RestClan
from ...error import *

router = APIRouter(tags=["clan"])


@router.get("/{region}/clan/", response_model=RestClan)
async def get_clan_session(region, name):
    try:
        return await ClanInterface(name=name, region=region).results()

    except BaseCustomException as e:
        raise HTTPException(status_code=404, detail=str(e))  # 404 - не найдено
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )  # 500 - ошибка сервера


@router.get("/clan/search")
async def search_clan(name):
    res = await ClanInterface(name=name).get_clans()
    if res:
        return res
    raise HTTPException(status_code=404, detail="Clan not found")
