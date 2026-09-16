"""Exercise real configured LLM and MCP services across Streamlit reruns."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT


def main():
    app = AppTest.from_file(ROOT / "app.py", default_timeout=180)
    checks = {}
    try:
        app.run()
        checks["startup"] = not app.exception and len(app.chat_input) == 1
        if not checks["startup"]:
            raise RuntimeError("Live UI startup failed; check setup verification")
        for question, route, tool in [
            ("Convert INR 50000 to SGD", "currency", "convert_currency"),
            ("What is the weather in Singapore tomorrow?", "weather", "get_weather_forecast"),
        ]:
            app.chat_input[0].set_value(question).run()
            entry = app.session_state["messages"][-1]
            provenance = entry.get("provenance", {})
            checks[route] = (
                not app.exception
                and provenance.get("route") == route
                and provenance.get("tools", {}).get(tool, {}).get("ok") is True
            )
        app.button[0].click().run()
        checks["clear_conversation"] = not app.exception and not app.session_state["messages"]
    finally:
        if "async_runner" in app.session_state:
            app.session_state["async_runner"].close()
    report = {"captured_at": datetime.now(timezone.utc).isoformat(), "checks": checks}
    (ROOT / "docs/live_ui_results.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(checks, indent=2))
    return all(checks.values())


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
