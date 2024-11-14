from functools import wraps
from fastapi import APIRouter, Query, Request, Cookie, Response, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse


from ...api.wotb import APIServer
from ...interfase.player import PlayerSession


def require_authentication(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request = kwargs.get("request")
        token = request.cookies.get("access_token", None)
        if not token:
            response = RedirectResponse(url="/login/eu")
            response.set_cookie("next_url", request.url.path)
            return response
        return await func(*args, **kwargs)

    return wrapper


class AuthController:
    def __init__(self):
        self.router = APIRouter(tags=["auth"])
        self.api_server = APIServer  # Инициализация API сервера
        self._setup_routes()

    def _setup_routes(self):
        self.router.add_api_route("/login/{region}", self.login, methods=["GET"])
        self.router.add_api_route("/logout", self.logout, methods=["GET"])
        self.router.add_api_route("/auth", self.auth, methods=["GET"])
        self.router.add_api_route(
            "/auth/verify", self.auth_verify_token, methods=["GET"]
        )

    async def login(self, region, response: Response):

        response.set_cookie("region", region, path="/", httponly=True)
        url = await self.api_server().get_token(reg=region)
        return {"susses": "ok", "url": url}
        # return JSONResponse(, headers=response.headers)

    @require_authentication
    async def logout(self, request: Request):
        token = request.cookies.get("access_token")
        await PlayerSession(access_token=token).logout()
        response = JSONResponse({"susses": "ok"})
        response.delete_cookie("access_token")
        return response

    async def auth(
        self,
        request: Request,
        background_tasks: BackgroundTasks,
        access_token: str = Query,
        nickname: str = Query,
        account_id: int = Query,
        expires_at: int = Query,
        region: str = Cookie(),
    ):

        pl = PlayerSession(
            name=nickname, id=account_id, reg=region, access_token=access_token
        )

        async def add_player_task():
            await pl.add_player()

        background_tasks.add_task(add_player_task)

        url = request.cookies.get("next_url", None)
        if url:
            # Формируем RedirectResponse
            response = RedirectResponse(url=url, status_code=302)
        else:
            response = JSONResponse(
                {"susses": "ok", "nickname": nickname, "region": region}
            )
        # Удаляем временные cookies, если они есть
        response.delete_cookie("next_url")
        response.delete_cookie("region")

        # Устанавливаем cookie для токена
        response.set_cookie("access_token", access_token, httponly=True, path="/")

        # Возвращаем RedirectResponse
        return response

    async def auth_verify_token(self, request: Request):
        token = request.cookies.get("access_token")
        return {"isAuthenticated": True} if token else {"isAuthenticated": False}


# Инициализация контроллера
auth_controller = AuthController()

# Регистрируем маршруты в основном приложении
router = auth_controller.router
