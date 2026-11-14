"""Live-data ingestion, upload and multi-format export for the SignalRadar demo.

This module keeps the demo path standard-library only (no Ollama / FAISS /
SentenceTransformers on the request path) while giving the UI a place to store
real financial text instead of only the bundled seed files.
"""

from __future__ import annotations

import csv
import io
import os
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF (optional, only for PDF extraction)

from ..config import BASE_DIR
from ..api.demo import router

# Where uploaded files and generated exports live.  A fresh checkout gets a
# small demo fixture created the first time this module is imported, so the UI
# never lands on a 404 purely because there is no data yet.
DATA_DIR = BASE_DIR / "data"
FILES_DIR = DATA_DIR / "files"
EXPORT_DIR = DATA_DIR / "exports"

# Seeded demo data lives in the same directory as the module, but uploads and
# exports never overwrite it.  The UI can merge uploaded events on top of this.
SEED_EVENTS_PATH = BASE_DIR / "backend" / "app" / "demo" / "events.json"
SEED_DIVERGENCE_PATH = BASE_DIR / "backend" / "demo" / "divergence.json"

STORAGE_FALLBACK = []
if "fitz" not in globals():
    STORAGE_FALLBACK = ["fitz"]


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def _load_seed_events() -> list[dict[str, Any]]:
    try:
        import json
        with open(SEED_EVENTS_PATH, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if isinstance(payload, dict):
            for key in ("events", "data", "items"):
                if isinstance(payload.get(key), list):
                    return payload[key]
            return [payload]
        return payload
    except Exception:
        return []


def _load_seed_divergence() -> dict[str, Any]:
    try:
        import json
        with open(SEED_DIVERGENCE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


@router.get("/demo/events/seed")
def seed_events():
    """Small demo payload so the UI does not stay empty during local-only runs."""
    return {
        "events": [
            {
                "id": "evt_seed_acme",
                "title": "Seeded event - Acme Technologies",
                "summary": "Demo event seeded from backend/app/demo/events.json.",
                "sentiment": "Bullish",
                "confidence": 0.85,
                "language": "en",
                "source": "demo seed",
                "entities": ["Acme Technologies"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "impact": 60,
                "evidence": "Seeded event text.",
            }
        ]
    }


@router.get("/demo/divergence/seed")
def seed_divergence():
    return {"divergence": _load_seed_divergence()}


def _artifacts() -> dict[str, Any]:
    """Return a summary of what is available: uploads + exports."""
    result: dict[str, Any] = {
        "uploaded_files": [],
        "exports": [],
    }

    try:
        for path in sorted(FILES_DIR.glob("*")):
            if path.is_file():
                result["uploaded_files"].append({
                    "id": path.name,
                    "name": path.name,
                    "size": path.stat().st_size,
                    "mime": "text/plain",
                    "created_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                })
    except Exception:
        pass

    try:
        for path in sorted(EXPORT_DIR.glob("*.json")) + sorted(EXPORT_DIR.glob("*.csv")) + sorted(EXPORT_DIR.glob("*.xlsx")):
            if path.is_file():
                suffix = path.suffix.lower()
                mime = {
                    ".json": "application/json",
                    ".csv": "text/csv",
                    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                }.get(suffix, "application/octet-stream")
                result["exports"].append({
                    "id": path.name,
                    "name": path.name,
                    "size": path.stat().st_size,
                    "mime": mime,
                    "created_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                })
    except Exception:
        pass

    return result


@router.get("/demo/data/artifacts")
def artifacts():
    _ensure_dirs()
    return _artifacts()


def _normalize_event(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        return {"text": obj}
    return None


def _events() -> list[dict[str, Any]]:
    """Event list = seed + uploads, aid in UI decisions."""
    events = _load_seed_events()
    try:
        import json
        for path in sorted(FILES_DIR.glob("events.json")):
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            if isinstance(payload, list):
                events.extend(payload)
            elif isinstance(payload, dict):
                for key in ("events", "data", "items"):
                    if isinstance(payload.get(key), list):
                        events.extend(payload[key])
    except Exception:
        pass
    return events


@router.get("/demo/data/events", response_model=list[dict[str, Any]])
def list_events():
    _ensure_dirs()
    events = _events()
    if not events:
        return _load_seed_events()
    return events


@router.get("/demo/data/divergence")
def get_divergence():
    _ensure_dirs()
    return _load_seed_divergence()


@router.post("/upload")
def upload(file: UploadFile = File(...), format: str = Form("json")):
    """Accept JSON, TXT, CSV, XLSX or PDF uploads."""
    _ensure_dirs()

    original = file.filename or ""
    accepted = {"json", "txt", "csv", "xlsx", "pdf"}
    fmt = (format or "").lower()
    if fmt not in accepted:
        return {"ok": False, "error": f"format must be one of {sorted(accepted)}"}

    tmp_fd: int | None = None
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{fmt}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_fd = tmp.fileno()
            tmp_path = Path(tmp.name)

        total = 0
        converted = []
        if fmt == "json":
            total, converted = _ingest_json(tmp_path)
        elif fmt == "txt":
            total, converted = _ingest_text(tmp_path, language=None)
        elif fmt == "csv":
            total, converted = _ingest_csv(tmp_path)
        elif fmt == "xlsx":
            total, converted = _ingest_xlsx(tmp_path)
        elif fmt == "pdf":
            total, converted = _ingest_pdf(tmp_path)

        # Persist everything uploaded so the UI can reuse the data later.
        events_file = FILES_DIR / "events.json"
        try:
            existing = []
            if events_file.exists():
                with open(events_file, "r", encoding="utf-8") as fh:
                    existing = json.load(fh)
            payload = existing + converted
            _dedupe_events(payload)
            with open(events_file, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
        except Exception:
            pass

        return {
            "ok": True,
            "filename": original,
            "format": fmt,
            "events_added": total,
            "total_events": len(_events()),
        }
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass


def _dedupe_events(events: list[dict[str, Any]]) -> None:
    seen = set()
    unique = []
    for event in events:
        identifier = event.get("id")
        if identifier:
            key = str(identifier)
        else:
            key = event.get("title", "") + "|" + event.get("text", "")
        if key and key not in seen:
            seen.add(key)
            unique.append(event)
    events.clear()
    events.extend(unique)


def _ingest_text(path: Path, language: str | None) -> tuple[int, list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    records = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        records.append({
            "id": f"evt_live_{datetime.now(timezone.utc).timestamp():.0f}_{len(records)}",
            "title": line[:200],
            "summary": line,
            "text": line,
            "language": language or "en",
            "source": "upload",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": None,
        })
    return len(records), records


def _ingest_json(path: Path) -> tuple[int, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    records: list[dict[str, Any]] = []
    if isinstance(payload, list):
        records = [r for r in payload if _normalize_event(r)]
    elif isinstance(payload, dict):
        for key in ("events", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                records = [r for r in value if _normalize_event(r)]
                break
        else:
            records = [r for r in (payload,)] if _normalize_event(payload) else []
    return len(records), records


def _ingest_csv(path: Path) -> tuple[int, list[dict[str, Any]]]:
    rows = list(csv.DictReader(io.TextIOWrapper(path.open("r", encoding="utf-8", errors="replace"), newline="")))
    records = []
    for row in rows:
        records.append({
            "id": f"evt_live_{datetime.now(timezone.utc).timestamp():.0f}_{len(records)}",
            "title": row.get("title") or row.get("text") or row.get("headline") or row.get("text", "")[:80],
            "summary": row.get("text") or row.get("summary") or row.get("description") or row.get("content") or row.get("headline") or "",
            "text": row.get("text") or row.get("body") or row.get("content") or "",
            "language": row.get("language") or "en",
            "source": "upload",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": None,
        })
    return len(records), records


def _ingest_xlsx(path: Path) -> tuple[int, list[dict[str, Any]]]:
    try:
        import openpyxl
    except Exception:
        return 0, []
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    records = []
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows(values_only=True):
            values = [str(cell).strip() if cell is not None else "" for cell in row]
            if not any(values):
                continue
            record = {
                "title": values[0][:200],
                "summary": values[1] if len(values) > 1 else "",
                "text": values[2] if len(values) > 2 else "",
                "language": values[3] if len(values) > 3 else "en",
                "source": "upload",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "confidence": None,
            }
            if any(record.get(field) for field in ("title", "summary", "text")):
                records.append(record)
    return len(records), records


def _ingest_pdf(path: Path) -> tuple[int, list[dict[str, Any]]]:
    language = None
    try:
        doc = fitz.open(str(path))
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text())
        text = "\n".join(text_parts)
    except Exception:
        text = path.read_text(encoding="utf-8", errors="replace")
    records = []
    for chunk in re.split(r"\n{2,}", text):
        chunk = chunk.strip()
        if not chunk:
            continue
        records.append({
            "id": f"evt_live_{datetime.now(timezone.utc).timestamp():.0f}_{len(records)}",
            "title": chunk[:200],
            "summary": chunk,
            "text": chunk,
            "language": language or "en",
            "source": "upload",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "confidence": None,
        })
    return len(records), records


@router.post("/ingest", response_model=dict[str, Any])
def ingest(events: list[dict[str, Any]]):
    """Accept event objects directly so the UI can push live financial text."""
    _ensure_dirs()
    new_events = [r for r in events if _normalize_event(r)]
    if not new_events:
        return {"ok": False, "error": "No valid events"}

    merged: list[dict[str, Any]] = []
    try:
        import json
        events_file = FILES_DIR / "events.json"
        if events_file.exists():
            with open(events_file, "r", encoding="utf-8") as fh:
                existing = json.load(fh)
            if isinstance(existing, list):
                merged = existing
    except Exception:
        merged = []

    merged.extend(new_events)
    _dedupe_events(merged)
    with open(FILES_DIR / "events.json", "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2, ensure_ascii=False)

    return {
        "ok": True,
        "events_added": len(new_events),
        "total_events": len(merged),
        "events": _events(),
    }


@router.delete("/data/clear-uploads")
def clear_uploads():
    """Remove uploaded data only, not the bundled seed files."""
    try:
        for path in FILES_DIR.glob("*"):
            if path.is_file():
                path.unlink(missing_ok=True)
    except Exception:
        pass
    return {"ok": True}


@router.get("/export")
def export(format: str = "json"):
    """Download events as JSON, CSV or Excel (xlsx)."""
    _ensure_dirs()
    events = _events()
    if not events:
        events = _load_seed_events()
    fmt = (format or "json").lower()
    if fmt not in {"json", "csv", "xlsx"}:
        fmt = "json"

    filename = f"signalradar_events_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.{fmt}"
    file_path = EXPORT_DIR / filename

    try:
        if fmt == "json":
            file_path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
        elif fmt == "csv":
            if events:
                with open(file_path, "w", encoding="utf-8", newline="") as fh:
                    writer = csv.DictWriter(fh, fieldnames=events[0].keys(), extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(events)
            else:
                file_path.write_text("id,title,language,source\n", encoding="utf-8")
        else:
            import openpyxl
            workbook = openpyxl.Workbook()
            worksheet = workbook.active
            if events:
                worksheet.append(list(events[0].keys()))
                for event in events:
                    worksheet.append([event.get(key, "") for key in event.keys()])
            workbook.save(file_path)
    except Exception:
        return {"ok": False, "error": "Could not generate export"}

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.get("/demo/hello")
def hello():
    return {"message": "SignalRadar demo API is live."}
