import os
import yaml
from ..models import ConfigStructure, Singleton


class Config(Singleton):

    def __init__(self) -> None:
        with open("settings.yaml", encoding="utf-8") as f:
            try:
                self.yaml_dict = yaml.safe_load(f)
                self.cfg = ConfigStructure.model_validate(self.yaml_dict)
            except Exception:

                raise RuntimeError("Failed to load settings.yaml")

    def get(self) -> ConfigStructure:
        """
        Return settings object.
        See struct in: `lib/data_classes/settings.py`
        """
        return self.cfg


class EnvConfig:
    LIMIT = int(os.getenv("LIMIT", "10"))
    WG_APP_IDS = os.getenv("WG_APP_IDS", "ccef3112e27c6158fe49486193a53a65")
    LT_APP_IDS = os.getenv("LT_APP_IDS")
    SECRET_KEY = os.getenv("SECRET_KEY", "SECRET_KEY")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "360"))
    SUPERUSER = os.getenv("SUPER_USER", "root")
    PASSWORD = os.getenv("PASSWORD", "root")
