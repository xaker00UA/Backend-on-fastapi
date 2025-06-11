from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from fastapi.requests import Request

from utils.interfase.admin import MetricsInterface
from utils.models.response_model import Command, LoginForm
from prometheus_client import generate_latest
from utils.server.admin.schemas import AdminStats
from utils.settings.logger import LoggerFactory
from ...database.admin import get_user, verify_password, create_access_token, valid


# FastAPI приложение
router = APIRouter(prefix="/admin", tags=["admin"])


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


@router.post("/commands")
async def protected_route(commands: Command, current_user=Depends(valid)):

    await commands.run()
    return {"command": "success"}


@router.get("/verify")
async def verify_token(admin=Depends(valid)):
    return admin


@router.get("/info", response_model=AdminStats)
async def info(requests: Request, limit: int = 100, current_user=Depends(valid)):
    service = MetricsInterface(requests.app.state.time)
    return await service.collect_all(limit=limit)
