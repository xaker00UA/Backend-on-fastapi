from pydantic import BaseModel


class StrMixin:
    def __str__(self) -> str:
        attributes = "\n".join(
            f"{key}={value}\n" for key, value in self.__dict__.items()
        )
        return f"{self.__class__.__name__}:\n{attributes}\n"


class Server(BaseModel, StrMixin):
    host: str
    port: str
    protocol: str


class Session(BaseModel, StrMixin):
    ttl: int


class AutoSession(BaseModel, StrMixin):
    ttl: int


class SessionWidget(BaseModel, StrMixin):
    url: str


class Auth(BaseModel, StrMixin):
    wg_redirect_uri: str
    wg_uri: str
    ds_auth_redirect_url: str
    ds_auth_primary_uri: str


class RegUrls(BaseModel, StrMixin):
    eu: str
    na: str
    asia: str


class Urls(BaseModel, StrMixin):
    get_id: str
    search: str
    get_stats: str
    get_achievements: str
    get_clan_stats: str
    get_tank_stats: str
    get_token: str
    longer_token: str
    get_position_rating: str
    logout: str
    search_clan: str
    get_clan_info: str
    get_tankopedia_tank: str
    get_tankopedia_achievements: str


class GameApi(BaseModel, StrMixin):
    reg_urls: RegUrls
    urls: Urls


class ConfigStructure(BaseModel, StrMixin):
    bot_name: str
    server: Server
    session: Session
    autosession: AutoSession
    session_widget: SessionWidget
    auth: Auth
    game_api: GameApi
