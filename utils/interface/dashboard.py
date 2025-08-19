from collections import defaultdict

from utils.models.response_model import RestUser
from utils.models.player import (
    UserDB,
)
from utils.database.Mongo import Player_all_sessions
from utils.error import *
from datetime import datetime
from loguru import logger as log


class DashboardInterface:
    def __init__(self):
        self.player_all_sessions = Player_all_sessions()

    def group_by_day_oldest(self, items: list[UserDB]):
        sessions_by_day = defaultdict(list)

        # Группировка по дате (YYYY-MM-DD)
        for item in items:
            date_str = datetime.fromtimestamp(item.timestamp).strftime("%Y-%m-%d")
            sessions_by_day[date_str].append(item)

        # Отбор самого старого item на каждый день
        filtered_items = []
        for day_items in sessions_by_day.values():
            oldest = max(day_items, key=lambda item: item.timestamp)
            filtered_items.append(oldest)

        return filtered_items

    async def get_player_stats_period(self, player_id, start_day, end_day):
        items = await self.player_all_sessions.get_period_sessions(
            player_id, start_day, end_day
        )
        filter_items = self.group_by_day_oldest(items)
        result_items = []
        for index in range(0, len(filter_items) - 1, 2):
            diff = (filter_items[index + 1] - filter_items[index]).result()
            if getattr(diff.general.session, "all", None) is not None:
                result_items.append(
                    {
                        "timestamp": filter_items[index].timestamp,
                        "value": diff,
                    }
                )
        res: list[RestUser] = [item.get("value") for item in result_items]
        return {
            "timestamp": [i.get("timestamp") for i in result_items],
            "survival": [i.general.session.all.survival for i in res],
            "damage": [i.general.session.all.damage for i in res],
            "wins": [i.general.session.all.winrate for i in res],
            "battles": [i.general.session.all.battles for i in res],
            "accuracy": [i.general.session.all.accuracy for i in res],
        }
