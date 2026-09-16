import pytest

from src.models import TravelPreferences
from src.orchestration.router import Router


@pytest.mark.parametrize(
    "question,route",
    [
        ("What are the must-visit attractions?", "destination_kb"),
        ("What is the weather in Singapore?", "weather"),
        ("Convert INR 50,000 to SGD.", "currency"),
        ("Plan 3 days next week based on weather.", "kb_weather"),
        ("I have INR 60,000. Convert it and plan 3 days.", "kb_currency"),
        ("Plan next week around weather and show INR 60,000 in SGD.", "kb_weather_currency"),
        ("Should I plan indoor or outdoor activities tomorrow?", "kb_weather"),
        ("How much is 200 SGD in INR?", "currency"),
        ("Hello", "general"),
        ("Weather forecast and convert INR 50000 to SGD", "weather_currency"),
    ],
)
async def test_routes(question, route):
    assert (await Router().decide(question, TravelPreferences())).route == route


async def test_money_and_duration():
    decision = await Router().decide("Convert INR 50,000 to SGD.", TravelPreferences())
    assert (decision.amount, decision.from_currency, decision.to_currency) == (50000, "INR", "SGD")
    decision = await Router().decide(
        "Create a three-day itinerary next week based on weather.", TravelPreferences()
    )
    assert decision.days == 3 and decision.start_date.weekday() == 0


async def test_missing_money():
    assert (await Router().decide("Convert to SGD", TravelPreferences())).clarification


async def test_foreign_destination_stops_before_tools():
    from unittest.mock import AsyncMock, Mock

    from src.orchestration.router import ScopeDecision

    model = Mock(
        with_structured_output=Mock(
            return_value=AsyncMock(ainvoke=AsyncMock(return_value=ScopeDecision(supported=False)))
        )
    )
    decision = await Router(model).decide("Weather in Paris", TravelPreferences())
    assert decision.route == "general" and not decision.needs_weather
