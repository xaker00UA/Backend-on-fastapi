from http import client
from fastapi import APIRouter, Body, Depends, Header
from fastapi.security import APIKeyHeader
from utils.interface import admin
from utils.interface.client import ClientInterface
from utils.models.response_model import Region, RestUser
from utils.server.client.schemas import CreateResponse
from utils.database.admin import valid
from loguru import logger as log

client_router = APIRouter(prefix="/client", tags=["client"])


api_key_scheme = APIKeyHeader(name="X-Token", auto_error=True)


def get_permissions(token: str = Depends(api_key_scheme)):
    valid(token)
    log.bind(name="root").info(f"Клиент {token.get("name")}")
    return token


@client_router.get(
    "/", response_model=RestUser, dependencies=[Depends(get_permissions)]
)
async def get_session(session_id: str):
    service = ClientInterface(session_id=session_id, name="_")
    return await service.results()


@client_router.post(
    "/",
    status_code=201,
    dependencies=[Depends(get_permissions)],
    response_model=CreateResponse,
)
async def create_session(name: str = Body(...), region: Region = Body(...)):
    service = ClientInterface(name=name, reg=region.value)
    session_id = await service.add_player()

    return CreateResponse(session_id=session_id, **service.user.model_dump())  # type: ignore


@client_router.delete("/", status_code=204, dependencies=[Depends(get_permissions)])
async def delete_session(session_id: str):
    service = ClientInterface(session_id=session_id, name="_")
    await service.delete_session()


@client_router.post(
    "/reset",
    status_code=201,
    dependencies=[Depends(get_permissions)],
    response_model=CreateResponse,
)
async def reset_session(session_id: str = Body(...)):
    service = ClientInterface(session_id=session_id, name="_")
    session_id = await service.reset()
    return CreateResponse(session_id=session_id, **service.user.model_dump())  # type: ignore
