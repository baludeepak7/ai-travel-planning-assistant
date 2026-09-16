# Demo script (5–8 minutes)

Before presenting, configure `.env`, ingest the KB, run `python scripts/verify_setup.py`,
`pytest -q`, and `python scripts/acceptance.py`. Start `streamlit run app.py`.
Enable Debug provenance. Connected means tool discovery succeeded, not guaranteed API uptime.

1. **Pure RAG (45 seconds)** — “What are the must-visit attractions in Singapore?”
   Show Knowledge Base, clickable citations, retrieved titles, destination_kb, no tool calls.
2. **Weather (45 seconds)** — “What is the weather forecast in Singapore for the next three days?”
   Show weather route, get_weather_forecast, provider, dates, fetched timestamp and current data.
   No KB sources section should appear. Explain this is a daily forecast, not a station reading.
3. **Currency (45 seconds)** — “Convert INR 50,000 to SGD.”
   Show convert_currency, actual published rate/date/provider, converted amount. Explain
   reference rates exclude bank fees; never insert prepared values if the provider fails.
4. **Combined plan (90 seconds)** — “Create a three-day Singapore itinerary for next week
   and adjust it according to the weather forecast.” Show kb_weather, retrieved indoor and
   outdoor evidence, actual weather calls, three days with indoor alternatives, source links,
   and AI planning note. Forecast ranges outside today+15 days must produce a limitation.
5. **Multi-turn (90 seconds)** — Clear conversation, then send:
   “We are two adults travelling with two children next week.”
   “Give us a three-day itinerary and avoid too much walking.”
   “Adjust it if rain is expected.”
   Show retained party/date/duration/mobility preferences and the final weather invocation.
6. **Budget (45 seconds)** — “I have a budget of INR 60,000. Convert it to SGD and suggest
   a three-day itinerary.” Show kb_currency, the MCP conversion and grounded economical choices.
   Exact affordability is not guaranteed without verified prices.
7. **Missing facts/failures (45 seconds)** — “What exhibits can I visit in Singapore's
   fictional Merlion Moon Observatory?” Show insufficient evidence rather than an invented fact.
   Ask “Weather in Singapore on 2099-01-01” to demonstrate a real MCP range failure.
   Unit tests exercise HTTP timeout/provider failures without changing production servers.

If generation or evidence verification fails, show the actual failure and resolve configuration;
do not substitute a handwritten itinerary or fake provider output.
