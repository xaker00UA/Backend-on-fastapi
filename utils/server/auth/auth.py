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


from ...api.wotb import APIServer
from ...interfase.player import PlayerSession


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


@router.get("/login/{region}")
async def login(region: str, redirect_url: str, response: Response):
    response.set_cookie("region", region, path="/", httponly=True)
    url = await PlayerSession.get_token(region=region, redirect_url=redirect_url)
    return {"susses": "ok", "url": url}


@router.get("/logout")
async def logout(token=Depends(require_authentication)):
    await PlayerSession(access_token=token).logout()
    response = JSONResponse({"susses": "ok"})
    response.delete_cookie("access_token")
    return response


@router.get("/auth")
async def auth(
    background_tasks: BackgroundTasks,
    access_token: str = Query(),
    nickname: str = Query(),
    account_id: int = Query(),
    region: str = Cookie(),
):
    player = PlayerSession(
        name=nickname, id=account_id, reg=region, access_token=access_token
    )
    background_tasks.add_task(player.add_player)
    response = JSONResponse({"susses": "ok", "nickname": nickname, "region": region})
    response.delete_cookie("region")
    response.set_cookie("access_token", access_token, httponly=True, path="/")
    return response


@router.get("/auth/verify")
async def auth_verify_token(access_token: str = Cookie(None)):
    return {"isAuthenticated": True} if access_token else {"isAuthenticated": False}
