"""SignalRadar demo endpoints.

Standalone by design: these routes never touch Ollama, SentenceTransformers or
FAISS, so the demo UI keeps working when the ML stack is unavailable.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.demo import loader


router = APIRouter(prefix="/demo", tags=["SignalRadar demo"])

_cache: dict[str, object] = {}


def _dashboard() -> dict:
    if "dashboard" not in _cache:
        _cache["dashboard"] = loader.build_dashboard()
    return _cache["dashboard"]  # type: ignore[return-value]


def _graph() -> dict:
    if "graph" not in _cache:
        dashboard = _dashboard()
        _cache["graph"] = loader.build_graph_payload(
            dashboard["events"],  # type: ignore[index]
            loader.load_graphs(),
        )
    return _cache["graph"]  # type: ignore[return-value]


class DemoQuery(BaseModel):
    query: str = Field(min_length=2, max_length=400)


@router.get("/dashboard")
def demo_dashboard() -> dict:
    try:
        return _dashboard()
    except Exception as error:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("/graph")
def demo_graph() -> dict:
    try:
        return _graph()
    except Exception as error:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.post("/query")
def demo_query(request: DemoQuery, limit: int = Query(default=4, ge=1, le=8)) -> dict:
    dashboard = _dashboard()
    result = loader.answer_query(
        request.query,
        dashboard["events"],  # type: ignore[index]
        _graph(),
    )
    result["citations"] = result["citations"][:limit]
    return result
