import httpx
import respx

from src.mcp_servers.currency_server import URL, convert_currency


@respx.mock
async def test_currency_output():
    respx.get(f"{URL}/rate/INR/SGD").mock(
        return_value=httpx.Response(
            200, json={"base": "INR", "quote": "SGD", "rate": 0.015, "date": "2026-01-02"}
        )
    )
    result = await convert_currency(60000, "INR", "SGD")
    assert result["ok"] and result["converted_amount"] == 900
    assert result["rate_date"] == "2026-01-02"


@respx.mock
async def test_provider_error():
    respx.get(f"{URL}/rate/INR/SGD").mock(return_value=httpx.Response(503))
    result = await convert_currency(50000, "INR", "SGD")
    assert not result["ok"] and "converted_amount" not in result


async def test_invalid_amount():
    for amount in (-1, float("inf"), float("nan")):
        assert not (await convert_currency(amount, "INR", "SGD"))["ok"]
