from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Cookie,
    Response,
    BackgroundTasks,
    status,
)
from fastapi.responses import RedirectResponse, JSONResponse

from utils.models.respnse_model import AuthLogin, AuthVerify, Region, RestUserDB
from ...interfase.player import PlayerSession
from utils.settings.logger import LoggerFactory


def get_region(req: Request, region: str | None = Cookie(default=None)) -> str | None:
    req
    return region


async def require_authentication(request: Request):
    token = request.cookies.get("access_token", None)
    if not token:
        # Если пользователь не авторизован
        response = RedirectResponse(url="/login/eu")
        response.set_cookie("next_url", request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated",
            headers={"Location": "/login/eu"},  # Необязательно, но полезно
        )
    # Если требуется дополнительная проверка токена, добавьте её здесь
    return (
        token  # Возвращает токен или другую информацию, если пользователь авторизован
    )


router = APIRouter(tags=["auth"])


@router.get("/login/{region}", response_model=AuthLogin)
async def login(region: Region, redirect_url: str, response: Response):
    response.set_cookie("region", region.value, path="/", httponly=True)
    url = await PlayerSession.get_token(region=region, redirect_url=redirect_url)
    return AuthLogin(url=url)


@router.get("/logout")
async def logout(token=Depends(require_authentication)) -> bool:
    await PlayerSession(access_token=token).logout()
    response = JSONResponse(content=True)
    response.delete_cookie("access_token")
    return response


@router.get("/auth")
async def auth(
    background_tasks: BackgroundTasks,
    access_token: str = Query(),
    nickname: str = Query(),
    account_id: int = Query(),
    region: str | None = Depends(get_region),
) -> RestUserDB:
    player = PlayerSession(
        name=nickname, id=account_id, reg=region, access_token=access_token
    )
    background_tasks.add_task(player.add_player)

    LoggerFactory.info(message=f"region:{region}")
    LoggerFactory.info(message=f"player:{player.user.model_dump()}")
    response = JSONResponse(content=RestUserDB(**player.user.model_dump()).model_dump())
    response.delete_cookie("region")
    response.set_cookie("access_token", access_token, httponly=True, path="/")
    return response


@router.get("/auth/verify")
async def auth_verify_token(access_token: str = Cookie(None)) -> AuthVerify:
    return (
        AuthVerify(isAuthenticated=True)
        if access_token
        else AuthVerify(isAuthenticated=False)
    )
