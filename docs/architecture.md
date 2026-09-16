# Architecture

Streamlit stores messages, a Pydantic TravelPreferences object, and per-session service
instances. A persistent asyncio Runner avoids reusing async model clients across closed
event loops on Streamlit reruns; Windows uses a Proactor loop for stdio subprocesses.

The context manager merges explicitly stated preferences. The router returns a validated
RouteDecision. Recognized intents use deterministic rules; unfamiliar paraphrases use
the configured LangChain model with structured output. Only selected capabilities run.
An additional weather_currency route avoids unnecessary RAG when both tools alone suffice.

RAG uses LangChain Documents, heading splits followed by 180-token chunks with 30-token
overlap. This accommodates local MiniLM's 256-wordpiece input limit and reduces truncation.
Real pretrained ONNX all-MiniLM-L6-v2
embeddings run on CPU; optional OpenAI embeddings use the same factory interface.
Chroma persists cosine vectors, full source metadata, and stable content/metadata hashes.
Repeated ingestion upserts matching hashes and removes obsolete chunks. Rebuild resets
the configured collection. Index metadata detects embedding-model/collection mismatches.

Ordinary retrieval returns up to RAG_TOP_K=5 chunks with cosine relevance >=0.3.
Plans retrieve up to six distinct chunks across itinerary, culture, museum, conservatory,
outdoor and transport queries. Scores are similarity signals, not truth probabilities.
Source title, URL, ID, section, document type, publisher, content format, license note and
review/retrieval date survive ingestion and retrieval. The five documents comprise three
Wikivoyage adaptations and two factual summaries grounded in official VisitSingapore pages.

MCPClient discovers two separate official-SDK FastMCP servers over stdio and exposes
their tools through langchain-mcp-adapters. Tool invocations use LangChain ToolCall envelopes
to preserve MCP structuredContent artifacts. The assistant never imports server functions
or calls provider HTTP endpoints. Each adapter invocation manages its own stdio session.
Only the servers know Open-Meteo and Frankfurter HTTP details.

Starting Streamlit initializes the client, which launches the server modules using the
same Python interpreter. Users do not start MCP servers separately. Streamlit listens on
localhost port 8501 by default; the MCP subprocesses use no HTTP listening ports. Chroma
is embedded and persists locally without a separate database server.

Destination synthesis uses structured facts with selected evidence IDs resolved to exact quotes, cited chunk IDs,
and recommendations with supporting IDs. Python checks IDs/quotes and itinerary completeness;
a second model call checks semantic support. At most two correction attempts repair evidence
or completeness failures without relaxing grounding. Unsupported output is withheld. Current tool
measurements are rendered directly in Python, independent of generative prose.

Errors fail closed. Missing/empty/incompatible KB does not trigger an ungrounded fallback.
Tool/API failures and forecast-range errors contain no manufactured observations or rates.
No authentication, booking, payments, navigation or deployment is included.
