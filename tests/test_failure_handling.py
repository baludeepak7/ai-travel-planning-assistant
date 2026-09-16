from unittest.mock import AsyncMock, Mock

import httpx
import respx

from src.mcp_client.client import MCPClient
from src.mcp_servers.weather_server import URL, get_weather_forecast
from src.models import TravelPreferences
from src.orchestration.assistant import MISSING, Verification
from src.services.date_service import singapore_today
from tests.test_orchestration import dependencies


@respx.mock
async def test_partial_weather_data_fails_closed():
    respx.get(URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "daily": {
                    "time": [singapore_today().isoformat()],
                    "weather_code": [None],
                    "temperature_2m_min": [25],
                    "temperature_2m_max": [31],
                    "precipitation_probability_max": [None],
                }
            },
        )
    )
    result = await get_weather_forecast("Singapore", singapore_today().isoformat(), 1)
    assert not result["ok"] and "forecast" not in result


async def test_broken_transport_returns_error():
    client = MCPClient()
    client.tools["convert_currency"] = Mock(
        ainvoke=AsyncMock(side_effect=RuntimeError("transport"))
    )
    result = await client.invoke("convert_currency", {})
    assert not result["ok"] and "rate" not in result


async def test_missing_tool_discovery_fails_startup():
    import pytest

    client = MCPClient()
    client.client.get_tools = AsyncMock(return_value=[])
    with pytest.raises(RuntimeError, match="discovery failed"):
        await client.initialize()


async def test_semantic_verifier_rejects_unsupported_claims():
    assistant, _, _ = dependencies()
    original = assistant.model.with_structured_output.side_effect
    assistant.model.with_structured_output.side_effect = lambda schema: (
        AsyncMock(ainvoke=AsyncMock(return_value=Verification(supported=False)))
        if schema is Verification
        else original(schema)
    )
    response = await assistant.respond("What attractions?", TravelPreferences())
    assert MISSING in response.markdown
    assert "Visit the museum" not in response.markdown
