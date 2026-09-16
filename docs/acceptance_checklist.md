# Assignment acceptance checklist

This maps the implementation to the Developer Assignment Brief. Completed means supported
by recorded validation, not a guarantee of every future generated answer or provider response.

## Minimum acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| At least three travel resources | Completed | Five documents: three Wikivoyage adaptations and two official VisitSingapore factual summaries |
| Embedding-based semantic retrieval | Completed | MiniLM, Chroma cosine search, 419 persisted chunks and real semantic integration tests |
| Grounded answers with source references | Completed | Evidence checks, title/URL citations and recorded destination answers |
| Weather through MCP | Completed | Real FastMCP stdio calls to Open-Meteo; forecast/provider metadata captured |
| Currency through MCP | Completed | Real FastMCP stdio calls to Frankfurter; conversion/rate date captured |
| Combined RAG and MCP response | Completed | Recorded three-day weather-aware itinerary with indoor alternatives; budget itinerary also captured |
| Multi-turn context | Completed | Family size, trip dates, duration and low-walking preferences retained across recorded follow-ups |
| Appropriate tool selection | Completed | Retrieval-only, tool-only and combined routing tests and live scenarios |
| Missing knowledge and tool failures | Completed | Unsupported-entity disclosure; timeout, invalid-date, malformed-result and transport tests |
| Simple usable interface | Completed | Streamlit chat, provenance, preferences, clear conversation, UI tests and HTTP health check |

## Required combined scenario

Prompt: “Create a three-day Singapore itinerary for next week and adjust it according to
the weather forecast.”

The application retrieves attractions, indoor/outdoor activities and transport guidance,
invokes the weather MCP tool, and generates day-wise recommendations with indoor alternatives.
The response separates retrieved facts, MCP information and AI planning choices, with citations.
See [recorded live responses](acceptance_results.json).

## Recorded validation

| Check | Result |
|---|---|
| Full automated suite, 2026-09-15 | 54 passed |
| Lint and format, 2026-09-15 | Ruff checks passed |
| Setup, 2026-09-15 | READY; five sources, 419 chunks and both MCP tools discovered |
| Repeat ingestion, 2026-09-15 | 419 chunks retained without duplicates |
| Official-source retrieval, 2026-09-15 | Both documents retrieved semantically with metadata preserved |
| Official-source live answers, 2026-09-15 | Two grounded answers cite the official summaries |
| Full live acceptance, 2026-09-14 | All 10 checks passed; predates official-source expansion |
| Live UI smoke capture | Startup, currency, weather and clear conversation passed |

Reports: [live acceptance](acceptance_results.json), [official-source answers](official_sources_results.json),
and [live UI](live_ui_results.json). Measurements retain their original timestamps and are not
current forecasts or rates. Full live acceptance has not been rerun after the official-source
expansion; subsequent validation includes the full automated suite and two targeted live answers.

Run `python -m pytest -q` for automated checks and `python scripts/verify_setup.py` for
configuration, index and discovery. The real-index tests need an ingested KB.
`python scripts/acceptance.py` and `python scripts/live_ui_smoke.py` use real services and
replace their timestamped reports. Keep the test directory for reproducibility.
| Short demonstration | Script ready; recording/presentation outstanding | Follow `demo_script.md` |

Git is not needed to run the app, but omitting repository delivery requires agreement from
the evaluator because the brief requests it. Tests are not required at runtime but are retained
as reproducible implementation evidence.
