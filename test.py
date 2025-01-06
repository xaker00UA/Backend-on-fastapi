from pydantic import BaseModel


class User(BaseModel):
    name: str


class UserLogin(User):
    password: str


class Player(BaseModel):
    id: int
    user: User


user = UserLogin(name="xakker", password="1234")

player = Player(id=123, user=user)
print(player.model_dump(serialize_as_any=True))
