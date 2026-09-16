from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, model_validator

from src.config import Settings
from src.services.date_service import singapore_today

mcp = FastMCP("Singapore Weather")
URL = "https://api.open-meteo.com/v1/forecast"


class ForecastDay(BaseModel):
    date: date
    condition: str
    weather_code: int
    temperature_min_c: float = Field(allow_inf_nan=False)
    temperature_max_c: float = Field(allow_inf_nan=False)
    precipitation_probability_max: float = Field(ge=0, le=100, allow_inf_nan=False)

    @model_validator(mode="after")
    def temperatures(self):
        if self.temperature_min_c > self.temperature_max_c:
            raise ValueError("Invalid temperature range")
        return self


def condition(code: int) -> str:
    if code == 0:
        return "Clear sky"
    if code in (1, 2, 3):
        return {1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast"}[code]
    if code in (45, 48):
        return "Fog"
    if code in (51, 53, 55, 56, 57):
        return "Drizzle"
    if code in (61, 63, 65, 66, 67):
        return "Rain"
    if code in (71, 73, 75, 77, 85, 86):
        return "Snow"
    if code in (80, 81, 82):
        return "Rain showers"
    if code in (95, 96, 99):
        return "Thunderstorm"
    return f"Unmapped WMO condition code {code}"


@mcp.tool()
async def get_weather_forecast(destination: str, start_date: str, days: int = 3) -> dict[str, Any]:
    """Retrieve Singapore daily forecast through Open-Meteo, within its 16-day window."""
    base = {
        "ok": False,
        "provider": "Open-Meteo",
        "source_url": URL,
        "destination": "Singapore",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        start = date.fromisoformat(start_date)
        if destination.strip().casefold() != "singapore" or not 1 <= days <= 16:
            return {**base, "error": "Only Singapore and 1–16 forecast days are supported."}
        end = start + timedelta(days=days - 1)
        today = singapore_today()
        if start < today or end > today + timedelta(days=15):
            return {
                **base,
                "error_code": "forecast_out_of_range",
                "error": "A reliable forecast is not available for these dates. "
                "The provider supports today through 15 days ahead.",
            }
        fields = [
            "weather_code",
            "temperature_2m_min",
            "temperature_2m_max",
            "precipitation_probability_max",
        ]
        async with httpx.AsyncClient(timeout=Settings().http_timeout_seconds) as client:
            response = await client.get(
                URL,
                params={
                    "latitude": 1.3521,
                    "longitude": 103.8198,
                    "timezone": "Asia/Singapore",
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "daily": ",".join(fields),
                },
            )
            response.raise_for_status()
            daily = response.json()["daily"]
        expected = [(start + timedelta(days=i)).isoformat() for i in range(days)]
        if daily["time"] != expected or any(len(daily[f]) != days for f in fields):
            raise ValueError("Incomplete forecast")
        forecast = [
            ForecastDay(
                date=day,
                condition=condition(daily["weather_code"][i]),
                weather_code=daily["weather_code"][i],
                temperature_min_c=daily["temperature_2m_min"][i],
                temperature_max_c=daily["temperature_2m_max"][i],
                precipitation_probability_max=daily["precipitation_probability_max"][i],
            ).model_dump(mode="json")
            for i, day in enumerate(expected)
        ]
        return {**base, "ok": True, "forecast": forecast}
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError):
        return {**base, "error": "Weather service unavailable or returned invalid data."}


if __name__ == "__main__":
    mcp.run(transport="stdio")
