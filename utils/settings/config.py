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
    WG_APP_IDS = os.getenv("WG_APP_IDS", "d54fbb4c26fae3290d5fb431a38ab932")
    LT_APP_IDS = os.getenv("LT_APP_IDS")