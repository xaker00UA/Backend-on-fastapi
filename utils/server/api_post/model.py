from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column

from utils.database.admin import Base


class PostOrm(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(unique=True)
    text: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now(), onupdate=datetime.now()
    )
