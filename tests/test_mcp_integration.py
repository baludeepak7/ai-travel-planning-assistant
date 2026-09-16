from src.mcp_client.client import MCPClient


async def test_real_stdio_discovery_and_invocation():
    client = MCPClient()
    await client.initialize()
    assert set(client.tools) == {"get_weather_forecast", "convert_currency"}
    # Validation paths still cross the real MCP transport; no HTTP or fake server needed.
    weather = await client.invoke(
        "get_weather_forecast", {"destination": "Singapore", "start_date": "2099-01-01", "days": 3}
    )
    currency = await client.invoke(
        "convert_currency", {"amount": -1, "from_currency": "INR", "to_currency": "SGD"}
    )
    assert weather.get("error_code") == "forecast_out_of_range"
    assert not currency["ok"] and "converted_amount" not in currency
