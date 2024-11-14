import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketState
from ...interfase.player import PlayerSession


class Connection_Manager:
    def __init__(self):
        self.active_connections: dict[WebSocket, dict[str, str]] = {}

    async def connect(self, region, name, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[websocket] = {"region": region, "name": name}

    def disconnect(self, websocket):
        self.active_connections.pop(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def get_new_params(self, websocket):
        v = self.active_connections.get(websocket)
        region = v.get("region")
        name = v.get("name")
        ses, update, user = await PlayerSession(name=name, reg=region).results()
        data = {
            "session": ses.model_dump(),
            "update": update.model_dump(),
            "user": user,
        }
        await self.send_personal_message(message=data, websocket=websocket)
        await asyncio.sleep(60)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


class Socket:
    def __init__(self):
        self.router = APIRouter()
        self.connection_manager = Connection_Manager()
        self._setup_routes()

    def _setup_routes(self):
        self.router.add_api_websocket_route("/ws/{name}", self.websocket_endpoint)

    async def websocket_endpoint(self, websocket: WebSocket, region, name):
        """
        WebSocket endpoint for real-time communication.
        - region: the region the player belongs to.
        - name: the name of the player.
        """
        await self.connection_manager.connect(region, name, websocket)
        try:
            while True:
                await self.connection_manager.get_new_params(websocket)
        except WebSocketDisconnect:
            self.connection_manager.disconnect(websocket)


router = Socket().router
