"""Live-data sync, upload and export helpers for the older KG-RAG branch.

This module keeps the demo path standard-library only (no Ollama / FAISS /
SentenceTransformers on the request path) while giving the UI a place to store
real financial text instead of only the bundled seed files.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Form, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from fastapi import APIRouter

from ..config import BASE_DIR

router = APIRouter()

from .analysis import router as analysis_router  # noqa: E402
from .graph import router as graph_router  # noqa: E402

# Where uploaded files and generated exports live.
DATA_DIR = BASE_DIR / "data"
FILES_DIR = DATA_DIR / "files"
EXPORT_DIR = DATA_DIR / "exports"

STORAGE_FALLBACK = []
if "fitz" not in globals():
    STORAGE_FALLBACK = ["fitz"]


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/demo/hello")
def hello():
    return {"message": "KG-RAG live-data sync API is live."}


@router.get("/demo/data/artifacts")
def artifacts():
    _ensure_dirs()
    result: dict[str, Any] = {"uploaded_files": [], "exports": []}
    try:
        for path in sorted(FILES_DIR.glob("*")):
            if path.is_file():
                result["uploaded_files"].append({
                    "id": path.name,
                    "name": path.name,
                    "size": path.stat().st_size,
                    "created_at": datetime.fromtimestamp(
                        path.stat().st_mtime, timezone.utc
                    ).isoformat(),
                })
    except Exception:
        pass
    try:
        for path in sorted(EXPORT_DIR.glob("*.json")) + sorted(
            EXPORT_DIR.glob("*.csv")
        ) + sorted(EXPORT_DIR.glob("*.xlsx")):
            if path.is_file():
                suffix = path.suffix.lower()
                mime = {
                    ".json": "application/json",
                    ".csv": "text/csv",
                    ".xlsx": "application/vnd.openxmlformats-officedocument."
                             "spreadsheetml.sheet",
                }.get(suffix, "application/octet-stream")
                result["exports"].append({
                    "id": path.name,
                    "name": path.name,
                    "size": path.stat().st_size,
                    "mime": mime,
                    "created_at": datetime.fromtimestamp(
                        path.stat().st_mtime, timezone.utc
                    ).isoformat(),
                })
    except Exception:
        pass
    return result


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    format: str = Form("json"),
):
    """Accept JSON, TXT, CSV, XLSX or PDF uploads and store them as events."""
    _ensure_dirs()
    original = file.filename or ""
    accepted = {"json", "txt", "csv", "xlsx", "pdf"}
    fmt = (format or "").lower()
    if fmt not in accepted:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": f"format must be one of {sorted(accepted)}"},
        )

    tmp_fd: int | None = None
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{fmt}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_fd = tmp.fileno()
            tmp_path = Path(tmp.name)

        total = 0
        if fmt == "json":
            total = _ingest_json(tmp_path)
        elif fmt == "txt":
            total = _ingest_text(tmp_path, language=None)
        elif fmt == "csv":
            total = _ingest_csv(tmp_path)
        elif fmt == "xlsx":
            total = _ingest_xlsx(tmp_path)
        elif fmt == "pdf":
            total = _ingest_pdf(tmp_path)

        events_file = FILES_DIR / "events.json"
        try:
            existing = []
            if events_file.exists():
                with open(events_file, "r", encoding="utf-8") as fh:
                    existing = json.load(fh)
            payload = existing + [{"text": r.get("text", "")} for r in _events()]
            with open(events_file, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
        except Exception:
            pass

        return {"ok": True, "filename": original, "format": fmt,
                "events_added": total, "total_events": len(_events())}
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass


def _ingest_text(path: Path, language: str | None) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    return sum(1 for line in text.splitlines() if line.strip())


def _ingest_json(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if isinstance(payload, dict):
            for key in ("events", "data", "items"):
                if isinstance(payload.get(key), list):
                    return len(payload[key])
            return 0
        return len(payload)
    except Exception:
        return 0


def _ingest_csv(path: Path) -> int:
    rows = list(csv.DictReader(io.TextIOWrapper(path.open("r", encoding="utf-8", errors="replace"), newline="")))
    return len(rows)


def _ingest_xlsx(path: Path) -> int:
    try:
        import openpyxl
    except Exception:
        return 0
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    return sum(1 for sheet in workbook.worksheets for row in sheet.iter_rows(values_only=True) if any(row))


def _ingest_pdf(path: Path) -> int:
    try:
        import fitz
        doc = fitz.open(str(path))
        return sum(1 for page in doc for _ in page.get_text().splitlines() if _.strip())
    except Exception:
        return 0


@router.post("/ingest")
def ingest(events: list[dict[str, Any]]):
    """Accept event objects directly so the UI can push live financial text."""
    merged: list[dict[str, Any]] = []
    try:
        events_file = FILES_DIR / "events.json"
        if events_file.exists():
            with open(events_file, "r", encoding="utf-8") as fh:
                existing = json.load(fh)
            if isinstance(existing, list):
                merged = existing
    except Exception:
        merged = []
    merged.extend(events)
    with open(FILES_DIR / "events.json", "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2, ensure_ascii=False)
    return {
        "ok": True,
        "events_added": len(events),
        "total_events": len(merged),
    }


@router.delete("/data/clear-uploads")
def clear_uploads():
    for path in FILES_DIR.glob("*"):
        if path.is_file():
            path.unlink(missing_ok=True)
    return {"ok": True}


@router.get("/export")
def export(format: str = "json"):
    _ensure_dirs()
    events = _events()
    fmt = (format or "json").lower()
    if fmt not in {"json", "csv", "xlsx"}:
        fmt = "json"
    filename = f"signalradar_events_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.{fmt}"
    file_path = EXPORT_DIR / filename
    try:
        if fmt == "csv":
            if events:
                with open(file_path, "w", encoding="utf-8", newline="") as fh:
                    writer = csv.DictWriter(fh, fieldnames=events[0].keys(), extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(events)
            else:
                file_path.write_text("id,title,language,source\n", encoding="utf-8")
        else:
            file_path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        return JSONResponse(status_code=500, content={"ok": False, "error": "Could not generate export"})
    return FileResponse(path=str(file_path), filename=filename, media_type="application/octet-stream")


def _events() -> list[dict[str, Any]]:
    try:
        events_file = FILES_DIR / "events.json"
        if events_file.exists():
            with open(events_file, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict):
                for key in ("events", "data", "items"):
                    if isinstance(payload.get(key), list):
                        return payload[key]
    except Exception:
        pass
    return []
