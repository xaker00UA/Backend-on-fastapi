ROUND_SECONDS = 43200  # 12 часов


def round_timestamp(ts: int, round_to: int = ROUND_SECONDS) -> int:
    return int((ts + round_to // 2) // round_to * round_to)
