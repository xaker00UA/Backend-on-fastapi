from enum import Enum
from typing import Awaitable, Callable, Optional, Union
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Response,
    status,
    Cookie,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from ...interfase.clan import ClanInterface
from ...interfase.player import PlayerSession
from pydantic import BaseModel, ConfigDict, Field, model_validator


from ...database.admin import get_user, verify_password, create_access_token, valid

import logging


class Commands(Enum):
    reset = "!reset_user"
    reset_clan = "!reset_clan"
    delete = "!delete_user"
    delete_clan = "!delete_clan"
    update_player_db = "!update_player_db"
    update_clan_db = "!update_clan_db"


class LoginForm(BaseModel):
    username: str
    password: str


class Regions(Enum):
    eu = "eu"
    na = "na"
    asia = "asia"


class Command(BaseModel):
    command: Commands
    region: Regions | None = None
    arguments: str = ""

    task: Callable | None = Field(default=None)

    def run(self):
        if self.task:
            return self.task

    @model_validator(mode="after")
    def convector(self):
        self.region = (
            self.region.value if isinstance(self.region, Regions) else self.region
        )
        return self

    @model_validator(mode="after")
    def valid(self):
        if self.command == Commands.reset:
            self.task = PlayerSession(name=self.arguments, reg=self.region).reset()
        elif self.command == Commands.reset_clan:
            self.task = ClanInterface(region=self.region, tag=self.arguments).reset()
        elif self.command == Commands.update_player_db:
            self.task = PlayerSession.update_db()
        elif self.command == Commands.update_clan_db:
            self.task = ClanInterface.update_db()
        elif self.command == Commands.delete:
            # Замените на нужное действие
            self.task = ...
        elif self.command == Commands.delete_clan:
            # Замените на нужное действие
            self.task = ...
        else:
            raise TypeError("Invalid command")
        return self


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
    try:
        await commands.run()
        return {"command": "success"}
    except Exception as e:
        logging.getLogger(__name__).exception(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify")
async def verify_token(admin=Depends(valid)):
    return admin
