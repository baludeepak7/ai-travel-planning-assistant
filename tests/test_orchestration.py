from unittest.mock import AsyncMock, Mock

from src.models import RetrievedChunk, TravelPreferences
from src.orchestration.assistant import (
    MISSING,
    Fact,
    GroundedAnswer,
    Recommendation,
    TravelAssistant,
    Verification,
)
from src.orchestration.router import Router


def dependencies():
    chunk = RetrievedChunk(
        source_id="guide",
        source_title="Guide",
        source_url="https://example.org",
        section="Museums",
        text="The museum is indoors.",
        relevance=0.8,
    )
    retriever = Mock()
    retriever.retrieve.return_value = [chunk]
    model = Mock()
    answer = GroundedAnswer(
        facts=[
            Fact(
                text="The museum is indoors.", chunk_id=0, supporting_quote="The museum is indoors."
            )
        ],
        recommendations=[
            Recommendation(
                title=f"Day {i}",
                plan="Visit the museum.",
                indoor_alternative="The museum.",
                chunk_ids=[0],
            )
            for i in range(1, 4)
        ],
    )
    model.with_structured_output.side_effect = lambda schema: AsyncMock(
        ainvoke=AsyncMock(
            return_value=answer
            if issubclass(schema, GroundedAnswer)
            else Verification(supported=True)
        )
    )
    mcp = Mock()
    mcp.invoke = AsyncMock(return_value={"ok": False, "error": "timeout"})
    return TravelAssistant(model, retriever, mcp, router=Router()), retriever, mcp


async def test_pure_currency_no_rag():
    assistant, retriever, mcp = dependencies()
    response = await assistant.respond("Convert INR 50000 to SGD", TravelPreferences())
    retriever.retrieve.assert_not_called()
    mcp.invoke.assert_awaited_once()
    assert "will not estimate" in response.markdown
    assert "Knowledge-base sources" not in response.markdown


async def test_pure_rag_no_tools():
    assistant, _, mcp = dependencies()
    response = await assistant.respond("What indoor attractions?", TravelPreferences())
    mcp.invoke.assert_not_called()
    assert "[Guide](https://example.org)" in response.markdown
    assert "MCP Current Information" not in response.markdown


async def test_combined_and_failure():
    assistant, retriever, mcp = dependencies()
    response = await assistant.respond(
        "Plan three days next week based on weather", TravelPreferences()
    )
    retriever.retrieve.assert_called_once()
    assert mcp.invoke.call_args.args[0] == "get_weather_forecast"
    assert "cannot reliably make weather-based adjustments" in response.markdown
    assert "Day 3" in response.markdown and "AI Recommendation" in response.markdown


async def test_empty_kb_no_synthesis():
    assistant, retriever, _ = dependencies()
    retriever.retrieve.return_value = []
    response = await assistant.respond("What attractions?", TravelPreferences())
    assert MISSING in response.markdown
    assistant.model.with_structured_output.assert_not_called()


async def test_invalid_evidence_rejected():
    assistant, _, _ = dependencies()
    assistant.model.with_structured_output = Mock(
        return_value=AsyncMock(
            ainvoke=AsyncMock(
                return_value=GroundedAnswer(
                    facts=[Fact(text="Invented", chunk_id=9, supporting_quote="fake")]
                )
            )
        )
    )
    response = await assistant.respond("What attractions?", TravelPreferences())
    assert "Invented" not in response.markdown and MISSING in response.markdown


async def test_budget_itinerary_calls_currency_and_rag():
    assistant, retriever, mcp = dependencies()
    response = await assistant.respond(
        "I have INR 60000. Convert it and plan 3 days.", TravelPreferences()
    )
    assert response.provenance.route == "kb_currency"
    retriever.retrieve.assert_called_once()
    assert mcp.invoke.call_args.args == (
        "convert_currency",
        {"amount": 60000, "from_currency": "INR", "to_currency": "SGD"},
    )
    assert "Day 3" in response.markdown and "will not estimate" in response.markdown


async def test_invalid_chunk_is_corrected_before_display():
    assistant, _, _ = dependencies()
    invalid = GroundedAnswer(
        facts=[
            Fact(
                text="The museum is indoors.",
                chunk_id=0,
                supporting_quote="The museum ... indoors.",
                evidence_id=99,
            )
        ]
    )
    valid = GroundedAnswer(
        facts=[
            Fact(
                text="The museum is indoors.", chunk_id=0, supporting_quote="The museum is indoors."
            )
        ]
    )
    generator = AsyncMock(ainvoke=AsyncMock(side_effect=[invalid, valid]))
    verifier = AsyncMock(ainvoke=AsyncMock(return_value=Verification(supported=True)))
    assistant.model.with_structured_output.side_effect = lambda schema: (
        generator if issubclass(schema, GroundedAnswer) else verifier
    )
    response = await assistant.respond("What indoor attractions?", TravelPreferences())
    assert generator.ainvoke.await_count == 2
    assert MISSING not in response.markdown and "The museum is indoors." in response.markdown


def test_partial_limitations_do_not_hide_supported_plan():
    answer = GroundedAnswer(
        missing_information=["Current ticket prices are not in the KB."],
        recommendations=[Recommendation(title="Day 1", plan="Visit the museum.", chunk_ids=[0])],
    )
    chunk = RetrievedChunk(
        source_id="guide",
        source_title="Guide",
        source_url="https://example.org",
        section="Museums",
        text="The museum is indoors.",
        relevance=0.8,
    )
    markdown = "\n".join(TravelAssistant.render_answer(answer, [chunk]))
    assert "Day 1" in markdown and "Current ticket prices" in markdown and MISSING not in markdown


def test_evidence_ids_resolve_only_to_original_source():
    import pytest

    from src.orchestration.assistant import resolve_evidence, valid_evidence

    chunk = RetrievedChunk(
        source_id="guide",
        source_title="Guide",
        source_url="https://example.org",
        section="Museums",
        text="The museum is indoors. It has art.",
        relevance=0.8,
    )
    answer = GroundedAnswer(
        facts=[
            Fact(
                text="It has art.",
                chunk_id=0,
                evidence_id=1,
                supporting_quote="Invented model quote",
            )
        ]
    )
    resolve_evidence(answer, [chunk])
    assert answer.facts[0].supporting_quote == "It has art."
    assert valid_evidence(answer, [chunk])
    answer.facts[0].evidence_id = 99
    with pytest.raises(ValueError):
        resolve_evidence(answer, [chunk])


def test_display_uses_source_quote_not_a_distorted_paraphrase():
    chunk = RetrievedChunk(
        source_id="guide",
        source_title="Guide",
        source_url="https://example.org",
        section="Museums",
        text="The museum is indoors.",
        relevance=0.8,
    )
    answer = GroundedAnswer(
        facts=[Fact(text="The museum is outdoors.", chunk_id=0, supporting_quote=chunk.text)]
    )
    markdown = "\n".join(TravelAssistant.render_answer(answer, [chunk]))
    assert "The museum is indoors." in markdown and "The museum is outdoors." not in markdown
