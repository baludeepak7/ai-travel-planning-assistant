import re

from pydantic import BaseModel, Field

from src.models import TravelPreferences
from src.orchestration.router import explicit_dates, money, normalized
from src.services.date_service import singapore_today


class PreferenceUpdate(BaseModel):
    preferences: TravelPreferences
    clear_fields: list[str] = Field(default_factory=list)


def merge_preferences(previous: TravelPreferences, patch: TravelPreferences, clear_fields=()):
    values = previous.model_dump()
    for key in clear_fields:
        if key in values and key != "destination":
            values[key] = [] if isinstance(values[key], list) else None
    for key, value in patch.model_dump(exclude_unset=True).items():
        if value is None or key == "destination":
            continue
        if isinstance(value, list):
            values[key] = list(dict.fromkeys(values[key] + value))
        else:
            values[key] = value
    return TravelPreferences(**values)


def explicit_preferences(message: str):
    text = normalized(message)
    values = {}
    for field, pattern in {
        "trip_days": r"\b(\d+)\s*days?\b",
        "adults": r"\b(\d+)\s*adults?\b",
        "children": r"\b(\d+)\s*(?:children|kids|child)\b",
    }.items():
        match = re.search(pattern, text)
        if match:
            values[field] = int(match[1])
    try:
        start = explicit_dates(message, singapore_today())
        if start:
            values["trip_start_date"] = start
    except ValueError:
        pass  # Router asks for correction; preserve any previously valid date.
    if re.search(r"avoid too much walking|less walking|low walking|limited mobility", text):
        values.update(pace="relaxed", mobility_notes="Avoid too much walking")
    if "no children" in text or "without children" in text:
        values["children"] = 0
    amount, currency = money(message)
    if amount is not None and "budget" in text:
        values.update(budget_amount=amount, budget_currency=currency)
    interests = [
        term
        for term in ("museums", "nature", "shopping", "history", "culture", "art")
        if term in text
    ]
    if interests:
        values["interests"] = interests
    food = [term for term in ("vegetarian", "vegan", "halal", "seafood") if term in text]
    if food:
        values["food_preferences"] = food
    if "trip_days" in values and not 1 <= values["trip_days"] <= 30:
        values.pop("trip_days")
    return TravelPreferences(**values)


class ContextManager:
    def __init__(self, model=None):
        self.model = model

    async def update(self, previous: TravelPreferences, message: str):
        merged = previous
        warning = None
        if self.model:
            try:
                patch = await self.model.with_structured_output(PreferenceUpdate).ainvoke(
                    [
                        (
                            "system",
                            "Extract ONLY newly stated Singapore trip preferences; leave unstated "
                            "fields null or empty. Never infer a budget from a standalone currency conversion. "
                            "Never infer party counts. Resolve next week to next Monday in Asia/Singapore. "
                            "Use clear_fields for explicit removals or list replacements; supply new values. "
                            "For corrections set the new value. Do not copy old values as new information. "
                            f"Today={singapore_today()}; previous={previous.model_dump_json()}",
                        ),
                        ("human", message),
                    ]
                )
                # Models sometimes populate an unstated date with today. A follow-up without
                # a temporal expression cannot change the saved date, even if extraction guessed one.
                has_date = bool(
                    re.search(
                        r"\b(today|tomorrow|yesterday|next|this|monday|tuesday|wednesday|thursday|friday|"
                        r"saturday|sunday|january|february|march|april|may|june|july|august|september|"
                        r"october|november|december|dates?|arrival|arrive|departure|depart)\b|"
                        r"\d{1,4}[-/]\d{1,2}",
                        message.lower(),
                    )
                )
                updates = patch.preferences
                if not has_date:
                    updates = updates.model_copy(update={"trip_start_date": None})
                explicit_clear = bool(
                    re.search(
                        r"\b(forget|remove|clear|replace|instead|switch|change)\b|no longer|rather than",
                        message.lower(),
                    )
                )
                clears = patch.clear_fields if explicit_clear else []
                if not has_date:
                    clears = [field for field in clears if field != "trip_start_date"]
                merged = merge_preferences(previous, updates, clears)
            except Exception:
                warning = (
                    "Some preferences could not be extracted. Explicit dates, party counts "
                    "and simple preferences were retained; check the sidebar."
                )
        return merge_preferences(merged, explicit_preferences(message)), warning
