from typing import Annotated
from fastapi import APIRouter, Depends
from httpx import post

from utils.server.admin.admin import is_admin_valid
from utils.server.api_post.schemas import RequestPost, ResponsePost, ResponsePosts
from utils.server.api_post.service import PostService


post_router = APIRouter(prefix="/post", tags=["post"])
service = Annotated[PostService, Depends(lambda: PostService())]


@post_router.get("/{id}", response_model=ResponsePost)
async def get_by_id_post(id: int, service: service):
    return service.get_by_id(id)


@post_router.get("/", response_model=ResponsePosts)
async def get_all(service: service, page: int = 1, size: int = 20):
    return service.get_all(page=page, page_size=size)


@post_router.post(
    "/",
    status_code=201,
    dependencies=[Depends(is_admin_valid)],
    response_model=ResponsePost,
)
async def post_create(service: service, data: RequestPost):
    return service.create(data)


@post_router.delete("/{id}", dependencies=[Depends(is_admin_valid)], status_code=204)
async def post_delete(service: service, id: int):
    return service.delete(id)


@post_router.put(
    "/{id}", dependencies=[Depends(is_admin_valid)], response_model=ResponsePost
)
async def update(service: service, id: int, data: RequestPost):
    return service.update(id, data)
