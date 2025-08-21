from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_serializer, model_serializer


class RequestPost(BaseModel):
    version: str
    text: str

    @field_serializer("version", when_used="json")
    def prefix_version(self, version):
        return f"v{version}"

    @model_serializer(mode="wrap")
    def reorder_fields(self, serializer, info):
        data = serializer(self, info)
        # Переупорядочим словарь: id первым, если он есть
        if hasattr(self, "id"):
            reordered = {"id": self.id}
            reordered.update({k: data[k] for k in data if k != "id"})
            return reordered
        return data


class ResponsePost(RequestPost):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ResponsePosts(BaseModel):
    items: list[ResponsePost]
    size: int
    page: int
    count: int
