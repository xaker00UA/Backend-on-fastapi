from datetime import datetime
from pydantic import BaseModel

from utils.models.player import UserDB


class CreateResponse(UserDB):
    session_id: str


class SessionResetRequest(BaseModel):
    session_id: str
