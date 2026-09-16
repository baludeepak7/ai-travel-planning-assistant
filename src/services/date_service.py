from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo


def singapore_today() -> date:
    return datetime.now(ZoneInfo("Asia/Singapore")).date()


def next_monday(today: date | None = None) -> date:
    today = today or singapore_today()
    return today + timedelta(days=7 - today.weekday())
