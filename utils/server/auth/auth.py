from datetime import timedelta
from urllib import response
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Cookie,
    Response,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse
from httpx import get

from utils.models.response_model import AuthLogin, AuthVerify, Region, RestUserDB
from utils.interface.player import PlayerSession
from utils.settings.logger import LoggerFactory
from utils.database.admin import create_access_token, valid


def get_region(region: str | None = Cookie(default=None)) -> str | None:
    return region


def get_token(token: str | None = Cookie(default=None)) -> str | None:
    if not token:
        return None
    payload = valid(token)
    return payload.get("access_token")


def require_authentication(token: str | None = Cookie(default=None)):
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    payload = valid(token)
    return payload.get("player_id")


router = APIRouter(tags=["auth"])


@router.get("/login/{region}", response_model=AuthLogin)
async def login(region: Region, redirect_url: str):
    url = await PlayerSession.get_token(region=region, redirect_url=redirect_url)
    response = JSONResponse(content=AuthLogin(url=url).model_dump())
    response.set_cookie("region", region.value, path="/", httponly=True)

    return response


@router.get("/logout")
async def logout(player_id: int = Depends(require_authentication)):
    # await PlayerSession(id=player_id).logout()
    response = JSONResponse(content=True)
    response.delete_cookie("token")
    return response


@router.get("/auth")
async def auth(
    background_tasks: BackgroundTasks,
    access_token: str = Query(),
    nickname: str = Query(),
    account_id: int = Query(),
    region: str | None = Depends(get_region),
):
    if not region:
        raise HTTPException(status_code=400, detail="region not found in cookies")
    player = PlayerSession(
        name=nickname, id=account_id, reg=region, access_token=access_token
    )
    background_tasks.add_task(player.add_player)
    token = create_access_token(
        {
            "name": nickname,
            "player_id": account_id,
            "region": region,
            "access_token": access_token,
        },
        expires_delta=timedelta(days=7),
    )
    LoggerFactory.log(message=f"player:{player.user.model_dump()}")  # type:ignore
    res = JSONResponse(content={"message": "ok"})
    res.delete_cookie("region")
    res.set_cookie(
        "token",
        token,
        httponly=True,
        path="/",
        expires=7 * 24 * 60 * 60,
    )

    return res
