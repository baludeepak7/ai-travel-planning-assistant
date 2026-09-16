"""Repeatable live acceptance checks. Never substitutes a mock for missing credentials."""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT, Settings
from src.llm_factory import chat_model
from src.mcp_client.client import MCPClient
from src.models import TravelPreferences
from src.orchestration.assistant import MISSING, TravelAssistant
from src.orchestration.context_manager import ContextManager
from src.rag.retriever import Retriever
from src.services.date_service import next_monday


def missing_knowledge_disclosed(markdown: str, entity: str) -> bool:
    if MISSING in markdown:
        return True
    # A specific, explicit limitation is also valid; the README's example wording is not mandatory.
    limitations = markdown.partition("### Knowledge-base limitations")[2].casefold()
    return entity.casefold() in limitations and any(
        phrase in limitations
        for phrase in ("does not contain", "does not list", "not enough information")
    )


async def main():
    settings = Settings()
    report = {"captured_at": datetime.now(timezone.utc).isoformat(), "checks": {}}
    checks = report["checks"]
    retriever = Retriever(settings)
    checks["three_sources_persisted"] = len(retriever.source_titles) >= 3 and retriever.count > 0
    chunks = retriever.retrieve("must-visit attractions in Singapore")
    checks["semantic_retrieval_and_metadata"] = bool(chunks) and all(
        c.source_title and c.source_url and c.section for c in chunks
    )
    client = MCPClient()
    await client.initialize()
    checks["mcp_discovery"] = len(client.tools) == 2
    weather = await client.invoke(
        "get_weather_forecast",
        {"destination": "Singapore", "start_date": next_monday().isoformat(), "days": 3},
    )
    currency = await client.invoke(
        "convert_currency", {"amount": 60000, "from_currency": "INR", "to_currency": "SGD"}
    )
    report["live_tool_results"] = {"weather": weather, "currency": currency}
    checks["live_weather_through_mcp"] = weather["ok"]
    checks["live_currency_through_mcp"] = currency["ok"]
    try:
        settings.validate_llm()
    except ValueError:
        checks["live_llm_scenarios"] = "BLOCKED: set OPENAI_API_KEY and OPENAI_MODEL in .env"
    else:
        model = chat_model(settings)
        assistant = TravelAssistant(model, retriever, client)
        manager = ContextManager(model)
        scenarios = [
            ("What are the must-visit attractions in Singapore?", "destination_kb"),
            (
                "Create a three-day Singapore itinerary for next week and adjust it according to "
                "the weather forecast.",
                "kb_weather",
            ),
            (
                "I have a budget of INR 60,000. Convert it to SGD and suggest a three-day itinerary.",
                "kb_currency",
            ),
        ]
        outputs = []
        for question, route in scenarios:
            prefs, _ = await manager.update(TravelPreferences(), question)
            response = await assistant.respond(question, prefs)
            checks[route] = (
                response.provenance.route == route
                and "Knowledge-base sources" in response.markdown
                and MISSING not in response.markdown
                and all(tool["ok"] for tool in response.provenance.tools.values())
            )
            if route in {"kb_weather", "kb_currency"}:
                checks[route] = checks[route] and all(
                    f"Day {day}" in response.markdown for day in range(1, 4)
                )
            outputs.append({"question": question, **response.model_dump(mode="json")})
        prefs = TravelPreferences()
        for question in [
            "We are two adults travelling with two children next week.",
            "Give us a three-day itinerary and avoid too much walking.",
            "Adjust it if rain is expected.",
        ]:
            prefs, _ = await manager.update(prefs, question)
        response = await assistant.respond(question, prefs)
        checks["live_multiturn"] = (
            prefs.adults == 2
            and prefs.children == 2
            and prefs.trip_days == 3
            and bool(prefs.mobility_notes)
            and prefs.trip_start_date == next_monday()
            and response.provenance.route == "kb_weather"
            and MISSING not in response.markdown
            and response.provenance.tools["get_weather_forecast"]["ok"]
        )
        report["multiturn"] = {
            "preferences": prefs.model_dump(mode="json"),
            "response": response.model_dump(mode="json"),
        }
        unknown = await assistant.respond(
            "What exhibits can I visit in Singapore's fictional Merlion Moon Observatory?",
            TravelPreferences(),
        )
        checks["missing_knowledge"] = missing_knowledge_disclosed(
            unknown.markdown, "Merlion Moon Observatory"
        )
        report["missing_knowledge_response"] = unknown.model_dump(mode="json")
        report["responses"] = outputs
    target = ROOT / "docs/acceptance_results.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(checks, indent=2))
    print(f"Report: {target}")
    return all(value is True for value in checks.values())


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
