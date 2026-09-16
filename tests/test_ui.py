from types import SimpleNamespace
from unittest.mock import AsyncMock

from streamlit.testing.v1 import AppTest

from src.config import ROOT
from src.models import AssistantResponse, Provenance, TravelPreferences
from src.orchestration.context_manager import ContextManager


def test_chat_preferences_provenance_and_clear(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-not-a-real-key")
    monkeypatch.setenv("OPENAI_MODEL", "unit-test-model")
    app = AppTest.from_file(ROOT / "app.py", default_timeout=15)
    app.session_state["assistant"] = SimpleNamespace(
        retriever=SimpleNamespace(count=415),
        mcp=SimpleNamespace(status={"weather": "Connected", "currency": "Connected"}),
        respond=AsyncMock(
            return_value=AssistantResponse(
                markdown="Preferences saved.",
                provenance=Provenance(route="destination_kb", rag_ran=True),
            )
        ),
    )
    app.session_state["context"] = ContextManager()
    app.run()
    assert not app.exception
    app.chat_input[0].set_value("We are two adults with two children next week").run()
    assert not app.exception and len(app.chat_message) == 2
    assert app.session_state["preferences"].children == 2
    assert any(e.label == "Sources & execution details" for e in app.expander)
    app.chat_input[0].set_value("Make it three days and avoid too much walking").run()
    assert app.session_state["preferences"].trip_days == 3
    assert app.session_state["preferences"].adults == 2
    app.button[0].click().run()
    assert not app.exception and len(app.chat_message) == 0
    assert app.session_state["preferences"] == TravelPreferences()
    app.session_state["async_runner"].close()
