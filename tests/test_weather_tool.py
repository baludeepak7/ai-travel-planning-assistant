from datetime import timedelta

import httpx
import respx

from src.mcp_servers.weather_server import URL, get_weather_forecast
from src.services.date_service import singapore_today


@respx.mock
async def test_weather_output():
    today = singapore_today().isoformat()
    respx.get(URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "daily": {
                    "time": [today],
                    "weather_code": [80],
                    "temperature_2m_min": [25],
                    "temperature_2m_max": [31],
                    "precipitation_probability_max": [75],
                }
            },
        )
    )
    result = await get_weather_forecast("Singapore", today, 1)
    assert result["ok"]
    assert result["forecast"][0]["condition"] == "Rain showers"


@respx.mock
async def test_weather_timeout():
    respx.get(URL).mock(side_effect=httpx.ReadTimeout("timeout"))
    result = await get_weather_forecast("Singapore", singapore_today().isoformat(), 1)
    assert not result["ok"] and "forecast" not in result


async def test_outside_forecast_window():
    result = await get_weather_forecast(
        "Singapore", (singapore_today() + timedelta(days=20)).isoformat(), 3
    )
    assert result["error_code"] == "forecast_out_of_range"
    assert "forecast" not in result


async def test_unsupported_destination():
    assert not (await get_weather_forecast("Paris", singapore_today().isoformat(), 1))["ok"]
