# AI Travel Planning Assistant

A context-aware Singapore travel assistant combining document-based destination knowledge
with weather forecasts and currency conversion through MCP. The Streamlit interface
separates knowledge-base facts, MCP information and AI recommendations, with citations.

## Completed assignment requirements

| Requirement | Implementation |
|---|---|
| Public destination knowledge | Five documents covering attractions, neighbourhoods, transport, culture, food and itineraries |
| Embedding-based semantic retrieval | LangChain, local MiniLM embeddings and persistent Chroma cosine search |
| Grounded answers with references | Retrieved evidence, original source titles/URLs, validation and missing-information handling |
| Weather through MCP | FastMCP server calling Open-Meteo for daily Singapore forecasts |
| Currency through MCP | FastMCP server calling Frankfurter for published reference rates |
| Combined RAG and MCP | Three-day weather-aware itineraries with indoor alternatives; budget conversion with suggestions |
| Multi-turn context | Retained group size, dates, duration, budget, interests, pace and food preferences |
| Appropriate tool selection | Validated routing selects retrieval, weather, currency or a combination |
| Failure handling | Missing knowledge and unavailable or malformed tool results produce explicit limitations |
| Simple usable interface | Streamlit chat, provenance, preferences and clear-conversation control |

See the [acceptance checklist](docs/acceptance_checklist.md) for evidence and deliverable status.

## Architecture and technology

Request flow: Streamlit → preference extraction → intent routing → RAG and/or MCP →
grounded synthesis and validation → cited response.

LangChain supplies model, prompt, retrieval and tool interfaces. Pydantic validates structured
outputs. The configured chat model is `gpt-5.4-mini`. Default embeddings use local ONNX
`all-MiniLM-L6-v2`; OpenAI `text-embedding-3-small` is an optional alternative.
Chroma stores vectors locally in `data/chroma/`. MCP integration uses the official Python
SDK, FastMCP and `langchain-mcp-adapters`.

Destination-only questions use retrieval without weather/currency calls. Tool-only requests
render actual MCP results directly. Combined requests use retrieved evidence and MCP results
for recommendations. See [architecture details](docs/architecture.md).

## Setup and local startup

Use Python 3.12 or newer. From the project directory, run in Windows CMD:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if not exist .env copy .env.example .env
```

If the environment is already installed, only activate it. Preserve an existing `.env`.
Set your API key and configuration in `.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-5.4-mini
OPENAI_REASONING_EFFORT=low
EMBEDDING_PROVIDER=local
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

With `local`, the OpenAI embedding setting is unused. Local embeddings download their model
on first use. Provider calls require internet access and may incur API usage charges.

Build the index once, check setup and start:

```bat
python scripts\ingest_kb.py
python scripts\verify_setup.py
python -m streamlit run app.py
```

Open [localhost:8501](http://localhost:8501). Keep the terminal running; Ctrl+C stops the app.
The index persists, so later starts only need the Streamlit command. Restart Streamlit after
re-ingestion. On macOS/Linux, use `python3 -m venv .venv`, `source .venv/bin/activate`,
and forward slashes for script paths. `requirements.txt` specifies dependencies;
`requirements.lock.txt` records the Windows versions used for the recorded validation.

### Server startup

The app automatically launches `src.mcp_servers.weather_server` and
`src.mcp_servers.currency_server` using its own Python interpreter. They communicate over
stdin/stdout, not HTTP ports. The adapter manages subprocess sessions for discovery and
invocation. No manual MCP startup is required. Chroma is embedded and needs no server.

### Switching embeddings

Set `EMBEDDING_PROVIDER=openai` and `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`,
then stop the app and run:

```bat
python scripts\ingest_kb.py --rebuild
python scripts\verify_setup.py
```

Stored chunks and questions must use the same model. The app detects incompatible indexes.

## Knowledge-base sources and RAG workflow

| Source | Stored document |
|---|---|
| [Singapore — Wikivoyage](https://en.wikivoyage.org/wiki/Singapore) | Adapted travel guide snapshot |
| [Marina Bay — Wikivoyage](https://en.wikivoyage.org/wiki/Singapore/Marina_Bay) | Adapted area guide snapshot |
| [Three days in Singapore — Wikivoyage](https://en.wikivoyage.org/wiki/Three_days_in_Singapore) | Adapted itinerary snapshot |
| [Gardens by the Bay — VisitSingapore](https://www.visitsingapore.com/neighbourhood/featured-neighbourhood/marina-bay/gardens-by-the-bay/) | Original factual summary grounded in the official page |
| [National Gallery — VisitSingapore](https://www.visitsingapore.com/neighbourhood/featured-neighbourhood/civic-district/national-gallery-singapore/) | Original factual summary grounded in the official page |

Documents are bundled in `data/raw/`; `data/source_manifest.yaml` records titles, URLs,
attribution and dates. Official-source documents are concise factual summaries, not full
article copies. Only Wikivoyage adaptations carry CC BY-SA 4.0 attribution.
See [source attribution and reuse](data/ATTRIBUTION.md).

Ingestion splits Markdown by heading, then into approximately 180-token chunks with
30-token overlap. The size accommodates MiniLM's input limit. Text, embeddings and source
metadata are stored together. Stable hashes prevent duplicates; re-ingestion removes obsolete
entries. The verified index has 419 chunks from five documents.

Retrieval embeds the question and searches by cosine similarity. Ordinary questions use up
to five chunks above the configured threshold. Plans retrieve across activity, indoor,
outdoor, culture and transport needs. Titles, URLs, sections, publishers and content types
survive retrieval and appear in provenance.

Refresh Wikivoyage with `python scripts/fetch_sources.py`, review changes and re-ingest.
Official summaries require manual review of their linked sources; the fetcher skips them.
Website scraping does not run during chat.

## MCP tools

| Tool | Inputs | Output |
|---|---|---|
| `get_weather_forecast` | Destination, start date, days | Daily conditions, temperature range, rain probability, provider and timestamp |
| `convert_currency` | Amount, source currency, target currency | Converted amount, reference rate, rate date, provider and timestamp |

Only the MCP servers call Open-Meteo and Frankfurter. The assistant invokes discovered tools
through its MCP client and retains structured results. Invalid or unavailable data is reported
without invented forecasts or rates. Weather requests must fit within today through today+15 days.

## Prompt and context strategy

Prompts restrict destination claims to retrieved evidence and current information to MCP
results. Structured answers separate facts, recommendations and missing information.
Evidence IDs resolve to stored text; the application renders citations and checks support.
A verification call reviews grounding. Failed answers receive at most two correction attempts
before being withheld. MCP measurements are rendered directly, not recreated by the model.

Structured preferences merge across turns, supplemented by the last eight messages.
Explicit corrections/removals are supported. Unrelated follow-ups cannot silently overwrite
saved trip dates. Dates use Asia/Singapore; next week means the next calendar Monday.
Clear conversation resets history and preferences. See [prompt details](docs/prompt_strategy.md).

## Tests, examples and demonstration

```bat
python -m pytest -q
python -m ruff check src tests scripts app.py
python scripts\live_tools.py
python scripts\acceptance.py
python scripts\live_ui_smoke.py
```

Recorded validation on 2026-09-15: 54 tests passed, Ruff passed and setup reported READY.
Real semantic search retrieved both official documents. The 2026-09-14 full live acceptance
capture has 10 successful checks and predates the official-source additions. Two targeted
live answers on 2026-09-15 verify citations to the new sources. These are dated observations.
Live scripts make real provider/model calls; unit tests use controlled responses for failure
scenarios. Production uses real services.

- [Sample questions and recorded responses](docs/sample_responses.md)
- [Acceptance criteria and deliverable status](docs/acceptance_checklist.md)
- [Live acceptance capture](docs/acceptance_results.json)
- [Official-source answers](docs/official_sources_results.json)



