"""Live external calls through real stdio MCP; saves no invented demo values."""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.mcp_client.client import MCPClient
from src.services.date_service import singapore_today


async def main():
    client = MCPClient()
    await client.initialize()
    results = {}
    results["weather"] = await client.invoke(
        "get_weather_forecast",
        {"destination": "Singapore", "start_date": singapore_today().isoformat(), "days": 3},
    )
    results["currency"] = await client.invoke(
        "convert_currency", {"amount": 50000, "from_currency": "INR", "to_currency": "SGD"}
    )
    print(json.dumps(results, indent=2))
    return all(r["ok"] for r in results.values())


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
