from datetime import date

from src.models import TravelPreferences
from src.orchestration.context_manager import ContextManager, merge_preferences
from src.orchestration.router import Router


async def test_multiturn_demo():
    manager = ContextManager()
    prefs, _ = await manager.update(
        TravelPreferences(), "We are two adults travelling with two children next week."
    )
    start = prefs.trip_start_date
    assert prefs.adults == 2 and prefs.children == 2 and start.weekday() == 0
    prefs, _ = await manager.update(
        prefs, "Give us a three-day itinerary and avoid too much walking."
    )
    prefs, _ = await manager.update(prefs, "Adjust it if rain is expected.")
    assert prefs.trip_days == 3 and prefs.pace == "relaxed"
    assert prefs.adults == 2 and prefs.children == 2 and prefs.trip_start_date == start
    decision = await Router().decide("Adjust it if rain is expected.", prefs)
    assert decision.route == "kb_weather" and decision.start_date == start


def test_merge_null_zero_lists_and_clear():
    prefs = TravelPreferences(children=2, trip_start_date=date(2026, 9, 14), interests=["art"])
    result = merge_preferences(
        prefs, TravelPreferences(children=0, trip_start_date=None, interests=["art", "nature"])
    )
    assert result.children == 0 and result.trip_start_date == prefs.trip_start_date
    assert result.interests == ["art", "nature"]
    assert merge_preferences(result, TravelPreferences(), ["interests"]).interests == []


async def test_currency_conversion_does_not_overwrite_budget():
    manager = ContextManager()
    prefs, _ = await manager.update(TravelPreferences(), "My budget is INR 60000")
    prefs, _ = await manager.update(prefs, "Convert 200 SGD to INR")
    assert prefs.budget_amount == 60000 and prefs.budget_currency == "INR"


async def test_model_cannot_invent_a_new_date_on_rain_followup():
    from unittest.mock import AsyncMock, Mock

    from src.orchestration.context_manager import PreferenceUpdate

    previous = TravelPreferences(trip_start_date=date(2026, 9, 21), trip_days=3, children=2)
    extracted = PreferenceUpdate(
        preferences=TravelPreferences(trip_start_date=date(2026, 9, 14)),
        clear_fields=["children", "trip_days"],
    )
    model = Mock(
        with_structured_output=Mock(
            return_value=AsyncMock(ainvoke=AsyncMock(return_value=extracted))
        )
    )
    result, _ = await ContextManager(model).update(previous, "Adjust it if rain is expected.")
    assert result.trip_start_date == previous.trip_start_date
    assert result.children == 2 and result.trip_days == 3
