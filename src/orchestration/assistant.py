import json
import logging
import re

from pydantic import BaseModel, Field, create_model

from src.models import AssistantResponse, Provenance, TravelPreferences
from src.orchestration.prompts import SYSTEM_PROMPT, VERIFIER_PROMPT
from src.orchestration.router import Router
from src.rag.citation import source_markdown, unique_sources

MISSING = "I do not have enough information in the travel knowledge base to answer that reliably."


class Fact(BaseModel):
    text: str
    chunk_id: int
    supporting_quote: str = ""
    evidence_id: int = Field(default=0, ge=0)


class Recommendation(BaseModel):
    title: str
    plan: str
    indoor_alternative: str = ""
    weather_consideration: str = ""
    chunk_ids: list[int] = Field(min_length=1)


class GroundedAnswer(BaseModel):
    facts: list[Fact] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


class Verification(BaseModel):
    supported: bool
    unsupported_claims: list[str] = Field(default_factory=list)


def render_tools(results):
    parts = []
    for name, result in results.items():
        if name == "get_weather_forecast":
            parts.append("### MCP Current Information — Weather")
            if not result["ok"]:
                parts.append(
                    "I could not retrieve the current Singapore weather forecast from the "
                    "MCP weather tool. I cannot reliably make weather-based adjustments right now."
                )
                if result.get("error_code") == "forecast_out_of_range":
                    parts.append(result["error"])
            else:
                for day in result["forecast"]:
                    parts.append(
                        f"- {day['date']}: {day['condition']}; "
                        f"{day['temperature_min_c']}–{day['temperature_max_c']} °C; "
                        f"rain probability {day['precipitation_probability_max']}%."
                    )
        else:
            parts.append("### MCP Current Information — Currency")
            if not result["ok"]:
                parts.append(
                    "I could not retrieve a current exchange rate from the MCP currency "
                    "tool, so I will not estimate the converted amount."
                )
            else:
                parts.append(
                    f"{result['amount']:,.2f} {result['from_currency']} = "
                    f"**{result['converted_amount']:,.2f} {result['to_currency']}**. "
                    f"Rate: {result['rate']}; rate date: {result['rate_date'] or 'not applicable'}."
                )
                parts.append("Reference rate; bank fees and retail spreads are not included.")
        parts.append(
            f"_MCP tool: `{name}`; provider: {result.get('provider', 'unavailable')}; "
            f"fetched: {result.get('fetched_at', 'unavailable')}._"
        )
    return "\n\n".join(parts)


def valid_evidence(answer, chunks):
    return not evidence_problems(answer, chunks)


def evidence_problems(answer, chunks):
    errors = []
    for index, fact in enumerate(answer.facts):
        if not 0 <= fact.chunk_id < len(chunks):
            errors.append(f"Fact {index}: chunk_id must be between 0 and {len(chunks) - 1}.")
            continue
        if not fact.supporting_quote.strip():
            errors.append(
                f"Fact {index}: select an evidence_id from chunk {fact.chunk_id}'s evidence_quotes."
            )
            continue
        if " ".join(fact.supporting_quote.split()) not in " ".join(
            chunks[fact.chunk_id].text.split()
        ):
            errors.append(
                f"Fact {index}: select a valid evidence_id from chunk {fact.chunk_id}'s "
                "evidence_quotes instead of reconstructing the supporting_quote."
            )
    for index, rec in enumerate(answer.recommendations):
        if any(not 0 <= i < len(chunks) for i in rec.chunk_ids):
            errors.append(
                f"Recommendation {index}: invalid chunk_ids {rec.chunk_ids}; "
                f"use zero-based IDs between 0 and {len(chunks) - 1}."
            )
    return errors


def evidence_quotes(text):
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def resolve_evidence(answer, chunks):
    """Resolve selected evidence IDs to exact source text, never model-reconstructed quotes."""
    for fact in answer.facts:
        if fact.evidence_id is not None:
            if not 0 <= fact.chunk_id < len(chunks):
                raise ValueError("Invalid chunk ID")
            quotes = evidence_quotes(chunks[fact.chunk_id].text)
            if not 0 <= fact.evidence_id < len(quotes):
                raise ValueError("Invalid evidence ID")
            fact.supporting_quote = quotes[fact.evidence_id]
            # Verify the exact text the UI will display, not an unused model paraphrase.
            fact.text = fact.supporting_quote


class TravelAssistant:
    def __init__(self, model, retriever, mcp, router=None):
        self.model, self.retriever, self.mcp = model, retriever, mcp
        self.router = router or Router(model)

    async def respond(self, message: str, preferences: TravelPreferences, history=None):
        decision = await self.router.decide(message, preferences)
        provenance = Provenance(route=decision.route)
        logging.info("[ROUTER] route=%s", decision.route)
        if decision.clarification:
            return AssistantResponse(markdown=decision.clarification, provenance=provenance)
        if decision.route == "general":
            return AssistantResponse(
                markdown="I can help plan Singapore travel using the knowledge "
                "base, weather forecasts and currency conversion. Tell me your dates and interests.",
                provenance=provenance,
            )
        chunks = []
        if decision.needs_rag:
            provenance.rag_ran = True
            query = message + " " + preferences.model_dump_json(exclude_none=True)
            if decision.needs_weather:
                query += " Singapore itinerary indoor museums outdoor gardens transportation"
            planning = bool(re.search(r"\b(plan|itinerary|adjust)\b", message.lower()))
            broad_attractions = bool(re.search(r"must.visit|attractions", message.lower()))
            chunks = self.retriever.retrieve(query, planning=planning or broad_attractions)
            provenance.sources = unique_sources(chunks)
        if decision.needs_weather:
            provenance.tools["get_weather_forecast"] = await self.mcp.invoke(
                "get_weather_forecast",
                {
                    "destination": "Singapore",
                    "start_date": decision.start_date.isoformat(),
                    "days": decision.days,
                },
            )
        if decision.needs_currency:
            provenance.tools["convert_currency"] = await self.mcp.invoke(
                "convert_currency",
                {
                    "amount": decision.amount,
                    "from_currency": decision.from_currency,
                    "to_currency": decision.to_currency,
                },
            )
        parts = [render_tools(provenance.tools)] if provenance.tools else []
        if decision.needs_rag:
            if not chunks:
                parts.append(MISSING)
            else:
                context = {
                    "question": message,
                    "preferences": preferences.model_dump(mode="json"),
                    "request": decision.model_dump(mode="json"),
                    "history": (history or [])[-8:],
                    "KNOWLEDGE_BASE_CONTEXT": [
                        dict(
                            chunk_id=i,
                            evidence_quotes=[
                                {"evidence_id": j, "quote": quote}
                                for j, quote in enumerate(evidence_quotes(c.text))
                            ],
                            **c.model_dump(),
                        )
                        for i, c in enumerate(chunks)
                    ],
                    "MCP_TOOL_RESULTS": provenance.tools,
                    "DISPLAYED_MCP_INFORMATION": render_tools(provenance.tools),
                }
                logging.info(
                    "[SYNTHESIS] rag=true weather=%s currency=%s",
                    decision.needs_weather,
                    decision.needs_currency,
                )
                try:
                    output_schema = GroundedAnswer
                    if planning:
                        output_schema = create_model(
                            "ItineraryAnswer",
                            __base__=GroundedAnswer,
                            recommendations=(
                                list[Recommendation],
                                Field(min_length=decision.days, max_length=decision.days),
                            ),
                        )
                    messages = [("system", SYSTEM_PROMPT), ("human", json.dumps(context))]
                    for attempt in range(3):
                        answer = await self.model.with_structured_output(output_schema).ainvoke(
                            messages
                        )
                        problems = []
                        try:
                            resolve_evidence(answer, chunks)
                        except ValueError:
                            problems.append(
                                "Select valid zero-based chunk_id and evidence_id values."
                            )
                        problems.extend(evidence_problems(answer, chunks))
                        if planning and answer.recommendations:
                            if len(answer.recommendations) != decision.days:
                                problems.append(f"Provide exactly {decision.days} day entries.")
                            if decision.needs_weather and any(
                                not rec.indoor_alternative for rec in answer.recommendations
                            ):
                                problems.append(
                                    "Each day needs an evidence-supported indoor alternative."
                                )
                            if decision.needs_weather:
                                for index, rec in enumerate(answer.recommendations):
                                    indoor = re.compile(r"museum|conservator|\bdomes?\b", re.I)
                                    if not indoor.search(rec.indoor_alternative) or not any(
                                        indoor.search(chunks[i].text)
                                        for i in rec.chunk_ids
                                        if 0 <= i < len(chunks)
                                    ):
                                        problems.append(
                                            f"Day {index + 1}: this KB only establishes museums "
                                            "and enclosed conservatories as indoor alternatives. Use one "
                                            "supported by the cited chunks; do not assume a meal stop, "
                                            "hawker centre or district is sheltered."
                                        )
                        if not problems:
                            verified = await self.model.with_structured_output(
                                Verification
                            ).ainvoke(
                                [
                                    (
                                        "system",
                                        VERIFIER_PROMPT + " List specific unsupported claims in "
                                        "unsupported_claims so the answer can be corrected; no internal reasoning.",
                                    ),
                                    (
                                        "human",
                                        json.dumps(context)
                                        + "\nCANDIDATE="
                                        + answer.model_dump_json(),
                                    ),
                                ]
                            )
                            if verified.supported:
                                break
                            problems = verified.unsupported_claims or [
                                "Remove any destination claims "
                                "that are not directly supported by the provided excerpts."
                            ]
                        if attempt == 2:
                            raise ValueError("Evidence validation failed after corrections")
                        logging.warning("[SYNTHESIS] correcting evidence: %s", json.dumps(problems))
                        messages = [
                            ("system", SYSTEM_PROMPT),
                            ("human", json.dumps(context)),
                            ("ai", answer.model_dump_json()),
                            (
                                "human",
                                "Return a COMPLETE replacement answer, not just the changed fields. "
                                "Retain all supported recommendations and include every requested day. "
                                "Correct these evidence/completeness issues using only the "
                                "same sources; do not weaken grounding: " + json.dumps(problems),
                            ),
                        ]
                    parts.extend(self.render_answer(answer, chunks))
                except Exception as exc:
                    logging.warning("[SYNTHESIS] answer withheld: %s", type(exc).__name__)
                    parts.append(
                        MISSING + " The grounded answer could not be generated or verified. "
                        "Check the configured LLM connection and try again."
                    )
                parts.append("### Knowledge-base sources\n" + source_markdown(provenance.sources))
                parts.append(
                    "_Attribution and content type are listed per source above. "
                    "Sources are dated travel knowledge, not verified current prices or rules._"
                )
        return AssistantResponse(markdown="\n\n".join(parts), provenance=provenance)

    @staticmethod
    def render_answer(answer, chunks):
        parts = []
        if answer.facts:
            parts.append("### Knowledge Base")
            parts.append(
                "_Dated source excerpts; descriptions of exhibitions, prices and hours "
                "are not verified current information._"
            )
        for fact in answer.facts:
            source = chunks[fact.chunk_id]
            parts.append(f"- {fact.supporting_quote} [{source.source_title}]({source.source_url})")
        if answer.recommendations:
            parts.append("### AI Recommendation")
        for rec in answer.recommendations:
            parts.append(f"#### {rec.title}\n{rec.plan}")
            if rec.weather_consideration:
                parts.append("**Weather consideration:** " + rec.weather_consideration)
            if rec.indoor_alternative:
                parts.append("**Indoor alternative:** " + rec.indoor_alternative)
            parts.append(source_markdown(unique_sources([chunks[i] for i in rec.chunk_ids])))
        if not (answer.facts or answer.recommendations):
            parts.append(MISSING)
        elif answer.missing_information:
            parts.append(
                "### Knowledge-base limitations\n"
                + "\n".join("- " + detail for detail in answer.missing_information)
            )
        if answer.recommendations:
            parts.append(
                "_AI planning note: sequencing, grouping and substitutions are AI-generated "
                "recommendations based on cited knowledge and the MCP results shown above._"
            )
        return parts
