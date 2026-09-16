from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class TravelPreferences(BaseModel):
    destination: Literal["Singapore"] = "Singapore"
    trip_start_date: date | None = None
    trip_days: int | None = Field(default=None, ge=1, le=30)
    adults: int | None = Field(default=None, ge=0)
    children: int | None = Field(default=None, ge=0)
    budget_amount: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    budget_currency: str | None = None
    interests: list[str] = Field(default_factory=list)
    pace: str | None = None
    mobility_notes: str | None = None
    food_preferences: list[str] = Field(default_factory=list)


class Source(BaseModel):
    source_id: str
    source_title: str
    source_url: str
    section: str
    document_type: Literal["travel_knowledge"] = "travel_knowledge"
    publisher: str = ""
    content_format: str = ""
    license: str = ""
    retrieved_at: str = ""


class RetrievedChunk(Source):
    text: str
    relevance: float


class Provenance(BaseModel):
    route: str
    rag_ran: bool = False
    sources: list[Source] = Field(default_factory=list)
    tools: dict[str, dict] = Field(default_factory=dict)


class AssistantResponse(BaseModel):
    markdown: str
    provenance: Provenance
