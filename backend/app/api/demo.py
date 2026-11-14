"""Demo API router (stdlib-only)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, Form, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel


@asynccontextmanager
async def _lifespan(app):
    yield


router = APIRouter(lifespan=_lifespan)

from ..demo import loader, uploader  # noqa: E402  (must follow the router definition)


class EventCreate(BaseModel):
    id: str | None = None
    title: str
    summary: str
    text: str | None = None
    sentiment: str | None = None
    confidence: float | None = None
    language: str | None = None
    source: str | None = None
    timestamp: str | None = None
    entities: list[str] | None = None
    impact: int | None = None
    evidence: str | None = None


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    context_window: int = 4000


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    citations: list[dict]
    related: list[dict]
    sentiment: str
    total_events: int


@router.post("/demo/query", response_model=QueryResponse)
def query(query: QueryRequest = Body(...)):
    """Map a natural-language question onto uploaded/seed events."""
    events = loader.list_events()
    query_text = (query.query or "").strip()
    if not events:
        return QueryResponse(
            answer="No events available.",
            confidence=0.0,
            citations=[],
            related=[],
            sentiment="neutral",
            total_events=0,
        )
    return loader.map_query(query_text, events, top_k=query.top_k)
