from __future__ import annotations

from datetime import datetime, timedelta

import pytz


def generate_publish_schedule(
    daily_slots: list[str],
    timezone_name: str,
    count: int,
) -> list[str]:
    if not daily_slots:
        raise ValueError("daily_slots cannot be empty")

    timezone = pytz.timezone(timezone_name)
    now_local = datetime.now(timezone)

    candidates: list[datetime] = []
    day_offset = 0
    while len(candidates) < count:
        base_day = now_local.date() + timedelta(days=day_offset)
        for slot in daily_slots:
            hour, minute = (int(p) for p in slot.split(":"))
            dt = timezone.localize(
                datetime(base_day.year, base_day.month, base_day.day, hour, minute)
            )
            if dt > now_local:
                candidates.append(dt)
                if len(candidates) == count:
                    break
        day_offset += 1

    return [
        dt.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        for dt in candidates
    ]
