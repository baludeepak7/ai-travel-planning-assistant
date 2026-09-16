from datetime import date

from src.orchestration.router import explicit_dates
from src.services.date_service import next_monday


def test_next_week_is_next_calendar_monday():
    assert next_monday(date(2026, 9, 11)) == date(2026, 9, 14)
    assert next_monday(date(2026, 9, 14)) == date(2026, 9, 21)
    assert explicit_dates("tomorrow", date(2026, 12, 31)) == date(2027, 1, 1)
