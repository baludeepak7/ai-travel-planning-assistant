import pytest

from src.config import Settings
from src.models import TravelPreferences


def test_missing_key():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        Settings(_env_file=None, openai_api_key="", openai_model="").validate_llm()


def test_preferences_defaults():
    assert TravelPreferences().destination == "Singapore"
    with pytest.raises(ValueError):
        TravelPreferences(trip_days=0)


def test_ui_setup_message(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_MODEL", "")
    from streamlit.testing.v1 import AppTest

    from src.config import ROOT

    app = AppTest.from_file(ROOT / "app.py").run()
    assert not app.exception
