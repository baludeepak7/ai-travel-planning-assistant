import math
import re
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from src.config import Settings

mcp = FastMCP("Singapore Currency")
URL = "https://api.frankfurter.dev/v2"


@mcp.tool()
async def convert_currency(
    amount: float, from_currency: str, to_currency: str = "SGD"
) -> dict[str, Any]:
    """Convert using the latest published Frankfurter reference rate, not a retail quote."""
    base = {
        "ok": False,
        "provider": "Frankfurter",
        "source_url": "https://frankfurter.dev/",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    source, target = from_currency.upper().strip(), to_currency.upper().strip()
    if (
        not math.isfinite(amount)
        or amount < 0
        or not all(re.fullmatch(r"[A-Z]{3}", code) for code in (source, target))
    ):
        return {**base, "error": "Use a nonnegative finite amount and three-letter currency codes."}
    try:
        async with httpx.AsyncClient(timeout=Settings().http_timeout_seconds) as client:
            if source == target:
                response = await client.get(f"{URL}/currencies")
                response.raise_for_status()
                if source not in {c["iso_code"] for c in response.json()}:
                    raise ValueError("Unsupported currency")
                return {
                    **base,
                    "ok": True,
                    "amount": amount,
                    "from_currency": source,
                    "to_currency": target,
                    "rate": 1,
                    "converted_amount": amount,
                    "rate_date": None,
                    "note": "Same currency; identity conversion, no FX rate.",
                }
            response = await client.get(f"{URL}/rate/{source}/{target}")
            response.raise_for_status()
            data = response.json()
        rate = Decimal(str(data["rate"]))
        rate_date = date.fromisoformat(data["date"])
        if (
            not rate.is_finite()
            or rate <= 0
            or data["base"] != source
            or data["quote"] != target
            or rate_date > datetime.now(timezone.utc).date()
        ):
            raise ValueError("Invalid exchange rate")
        converted = (Decimal(str(amount)) * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            **base,
            "ok": True,
            "amount": amount,
            "from_currency": source,
            "to_currency": target,
            "rate": float(rate),
            "converted_amount": float(converted),
            "rate_date": rate_date.isoformat(),
        }
    except (httpx.HTTPError, ValueError, KeyError, TypeError, ArithmeticError):
        return {
            **base,
            "error": "Currency provider unavailable, invalid response, or unsupported currency.",
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
