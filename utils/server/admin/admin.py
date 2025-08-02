from typing import Annotated
from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    status,
)
from fastapi.requests import Request

from utils.interface.admin import AdminInterface, MetricsInterface
from utils.models.response_model import ItemTank, LoginForm
from prometheus_client import generate_latest
from utils.server.admin.schemas import AdminStats, CommandRequest, CreateTank
from utils.settings.logger import LoggerFactory
from ...database.admin import get_user, verify_password, create_access_token, valid
from fastapi import UploadFile

# FastAPI приложение
router = APIRouter(prefix="/admin", tags=["admin"])


def is_admin_valid(admin_token: str = Cookie("admin_token")):
    return valid(admin_token)


# Эндпоинты
@router.post("/login")
async def login(
    response: Response,
    form_data: LoginForm,
):
    user = get_user(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    response.set_cookie(key="admin_token", value=access_token, httponly=True)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="admin_token")
    return {"message": "Logged out"}


@router.post("/commands", status_code=202, dependencies=[Depends(is_admin_valid)])
async def protected_route(
    commands: CommandRequest, current_user=Depends(is_admin_valid)
):
    await commands.run()
    return {"command": "success"}


@router.get("/verify")
async def verify_token(admin=Depends(is_admin_valid)):
    return admin


@router.get("/info", response_model=AdminStats)
async def info(
    requests: Request, limit: int = 100, current_user=Depends(is_admin_valid)
):
    service = MetricsInterface(requests.app.state.time)
    return await service.collect_all(limit=limit)


@router.post(
    "/add_tank",
    status_code=201,
    dependencies=[Depends(is_admin_valid)],
    response_model=CreateTank,
)
async def add_tank(
    tank_id: Annotated[int, Form()],
    name: Annotated[str, Form()],
    nation: Annotated[str, Form()],
    tier: Annotated[int, Form()],
    is_premium: Annotated[bool, Form()],
    image_big: Annotated[UploadFile | None, File()] = None,
    image_small: Annotated[UploadFile | None, File()] = None,
):
    service = AdminInterface()
    tank = CreateTank(
        tank_id=tank_id,
        name=name,
        nation=nation,
        tier=tier,
        is_premium=is_premium,
    )
    return await service.add_tank(
        tank_data=tank, image_big=image_big, image_small=image_small
    )
