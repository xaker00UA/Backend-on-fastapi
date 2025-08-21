from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from utils.database.admin import SessionLocal
from utils.server.api_post.model import PostOrm
from utils.server.api_post.schemas import RequestPost
from sqlalchemy import func, update, select


class PostService:
    def __init__(self, session: Session | None = None):
        if session:
            self.db: Session = session
        else:
            self.db: Session = SessionLocal()

    def create(self, data: RequestPost):
        post = PostOrm(**data.model_dump())
        try:
            self.db.add(post)
            self.db.commit()
            self.db.refresh(post)
            return post
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                detail="Post with this title already exists", status_code=409
            )

    def delete(self, id: int):
        post = self.get_by_id(id)
        post = self.db.delete(post)
        self.db.commit()

    def update(self, id: int, data: RequestPost):
        stmt = update(PostOrm).where(PostOrm.id == id).values(**data.model_dump())
        try:
            self.db.execute(stmt)
            self.db.commit()
            return self.db.get(PostOrm, id)
        except IntegrityError:
            raise HTTPException(
                detail="Post with this title already exists", status_code=409
            )

    def get_all(self, page: int = 1, page_size: int = 20):
        stmt = select(PostOrm).offset((page - 1) * page_size).limit(page_size)
        result = self.db.execute(stmt)
        items = result.scalars().all()
        count_stmt = select(func.count()).select_from(PostOrm)
        total = self.db.execute(count_stmt).scalar()

        return {"items": items, "page": page, "size": page, "count": total}

    def get_by_id(self, id: int):
        post = self.db.get(PostOrm, id)
        if post:
            return post
        raise HTTPException(status_code=404, detail="Post not found")
