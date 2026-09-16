# Sample questions and application responses

The table describes expected behavior. Actual response excerpts appear below; complete
timestamped captures are linked. Generated responses require the configured LLM.

| Question | Expected route and visible result |
|---|---|
| What are the must-visit attractions in Singapore? | destination_kb; supported attractions with title/URL citations; no tools |
| Which neighbourhoods are suitable for cultural experiences? | destination_kb; retrieved cultural neighbourhood evidence and citations |
| How can a tourist travel around Singapore? | destination_kb; retrieved MRT/bus guidance; no invented current fares |
| Suggest activities for a family with children. | destination_kb; grounded family suggestions, labeled AI Recommendation |
| What indoor attractions can I visit? | destination_kb; supported indoor options, missing details acknowledged |
| What is the weather in Singapore? | weather; actual MCP forecast, provider, timestamp; no KB section |
| What is the forecast for the next three days? | weather; exactly the requested dates from MCP |
| Should I plan indoor or outdoor activities tomorrow? | kb_weather; current forecast plus grounded activity recommendations |
| Convert INR 50,000 to SGD. | currency; actual rate, date and converted amount from MCP |
| How much is 200 SGD in INR? | currency; reverse direction, latest published rate |
| Create a three-day Singapore itinerary for next week and adjust it according to the weather forecast. | kb_weather; three days, weather considerations, indoor alternatives and source links |
| I have a budget of INR 60,000. Convert it to SGD and suggest a three-day itinerary. | kb_currency; actual conversion, grounded economical suggestions, no invented ticket-price totals |
| Suggest outdoor attractions and replace them with indoor options if rain is expected. | kb_weather; evidence-supported alternatives based on MCP results |

Failure text includes:

> I do not have enough information in the travel knowledge base to answer that reliably.

> I could not retrieve the current Singapore weather forecast from the MCP weather tool.
> I cannot reliably make weather-based adjustments right now.

> I could not retrieve a current exchange rate from the MCP currency tool, so I will not
> estimate the converted amount.

Current measurements are deliberately absent from this Markdown document. Re-run the live
acceptance script to capture new measurements with their original fetched/rate timestamps.

## Recorded destination response excerpts

These excerpts were produced by the application on 2026-09-15 and are stored in
[the official-source response capture](official_sources_results.json).

Question: “What functions do the Supertrees at Gardens by the Bay serve?”

> The Supertrees support vertical planting.
>
> Their functions include harvesting rainwater, producing solar energy and ventilating conservatories.

The answer cites the [VisitSingapore Gardens by the Bay page](https://www.visitsingapore.com/neighbourhood/featured-neighbourhood/marina-bay/gardens-by-the-bay/)
through the stored factual summary. It also includes a cited Wikivoyage excerpt.

Question: “What art does National Gallery Singapore collect?”

> The gallery focuses on Southeast Asian art.
>
> VisitSingapore describes a collection exceeding 8,000 works, spanning the nineteenth century onward.

The answer cites the [VisitSingapore National Gallery page](https://www.visitsingapore.com/neighbourhood/featured-neighbourhood/civic-district/national-gallery-singapore/)
through the stored factual summary. These are dated knowledge statements.

## Combined responses and conversation

[The full live acceptance capture](acceptance_results.json) contains actual weather-aware
and budget itineraries, including the original provider values and source citations.
It also records the preferences and answer from this multi-turn sequence:

1. “We are two adults travelling with two children next week.”
2. “Give us a three-day itinerary and avoid too much walking.”
3. “Adjust it if rain is expected.”

The captured context retains group size, date, duration and walking preference.
