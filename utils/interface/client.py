from loguru import logger
from utils.database.Mongo import Client_DB
from utils.error.exception import *
from utils.interface.player import PlayerSession


class ClientInterface(PlayerSession):
    player_repo = Client_DB

    def __init__(self, session_id: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id

    async def add_player(self) -> str:
        await self.get_player_details()
        session_id = await self.player_repo.add(self.user)  # type: ignore
        return session_id

    async def get_player_DB(self):
        if not self.session_id:
            raise TypeError("session_id not found")
        self.old_user = await self.player_repo.get(self.session_id)
        if not self.old_user:
            raise NotFoundPlayerDB(session_id=self.session_id)

    async def delete_session(self):
        if not self.session_id:
            raise TypeError("session_id not found")
        if not await self.player_repo.delete(self.session_id):
            logger.bind(name="root").error(
                "Ошибка удаления сессии", session_id=self.session_id
            )
            raise NotFoundPlayerDB(session_id=self.session_id)

    async def reset(self) -> str:
        await self.get_player_DB()
        self.user = self.old_user
        await self.delete_session()
        return await self.add_player()
