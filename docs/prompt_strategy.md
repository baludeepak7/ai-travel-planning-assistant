# Prompt and context strategy

`src/orchestration/prompts.py` is the shared grounding policy. Facts about Singapore must
come from retrieved chunks; current weather and currency must come from real MCP results.
The model cannot use memory to fill missing destination facts. It must distinguish facts
from its recommended day ordering. Prices, hours and rules in snapshots are dated and
must not be presented as verified current information.

The synthesis schema separates Fact, Recommendation and missing_information. Facts select
numbered evidence snippets; Python resolves these IDs to exact source quotes so the model
does not have to recopy source punctuation. All chunk and evidence IDs must exist. The
displayed KB facts use those original excerpts, and the verifier reviews that exact text.
An independent structured verification call reviews semantic support and preference adherence.
Python renders source title/URL citations. It also checks day-count and indoor alternatives
for itinerary requests. Rejected responses show an explicit insufficient-information message.
Failed evidence or completeness checks get at most two correction attempts with the same
sources. Unverified answers remain withheld. The verifier distinguishes permitted AI ranking
and sequencing from unsupported destination facts. Missing optional details, such as current
ticket prices, are shown as specific limitations alongside the supported plan.
The itinerary output schema enforces the requested number of days. The verifier also sees
the separately rendered MCP section so it does not demand duplicate currency/weather figures
from generated prose. This improves grounding but is not a mathematical guarantee against
model mistakes.

Tool-only answers bypass generative synthesis: actual MCP result values become Markdown.
Mixed answers display those values separately from the generated grounded plan. Tool failures
produce fixed, explicit no-estimation messages. The model must not claim weather adjustment
when forecast data is unavailable.

Context extraction uses structured output for natural-language dates, pace, accessibility,
interests, dietary preferences and corrections. Deterministic extraction reinforces explicit
numbers and common phrases. Only non-null updates merge; list preferences deduplicate;
explicit clear_fields support removal and replacement. Zero children is preserved as a real
update. A standalone conversion does not replace the travel budget.
Date changes require a temporal expression in the new message; a model-generated date cannot
overwrite a saved trip date on an unrelated follow-up. Field clearing requires explicit wording.

`next week` means next calendar Monday, based on Asia/Singapore. Defaults are today and
three forecast days when nothing is specified. ISO dates are recommended for clarity.
The last eight messages supplement structured preferences; earlier prose is not authoritative
for weather or rates. Clear conversation resets both history and preferences.

Retrieved content is untrusted data. Provenance exposes route, source metadata and actual
tool results only. No chain-of-thought is displayed or logged.
