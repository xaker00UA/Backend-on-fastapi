import asyncio
from fastapi import APIRouter, WebSocket

from utils.models.response_model import Region
from ...interface.player import PlayerSession


router = APIRouter(prefix="/ws")


@router.websocket("/{name}")
async def websocket_endpoint(websocket: WebSocket, region: Region, name: str):
    await websocket.accept()
    player = PlayerSession(name=name, reg=region)
    while True:
        data = await player.results()
        await websocket.send_json(data.model_dump())
        await asyncio.sleep(60)
