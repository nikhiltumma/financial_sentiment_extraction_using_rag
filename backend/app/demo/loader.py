"""SignalRadar demo data layer.

Normalises the saved knowledge graphs and the curated seed files into the small
payloads the demo UI needs. Everything here is standard library only: no
Ollama, no SentenceTransformers, no FAISS, so the demo stays up when the ML
stack or the model server is unavailable.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
GRAPH_DIR = PROJECT_ROOT / "knowledge_graphs"
DEMO_DIR = Path(__file__).resolve().parent

SENTIMENT_SCORE = {"Bullish": 1.0, "Neutral": 0.0, "Bearish": -1.0}
IMPACT_BASE = {"Bullish": 52, "Bearish": 58, "Neutral": 38}
LANGUAGE_LABELS = {"en": "English", "hi": "Hindi", "te": "Telugu"}

FIELD_WEIGHTS = {"title": 2.0, "entities": 1.6, "evidence": 1.2, "summary": 1.0}

STOPWORDS = {
    "the", "and", "for", "with", "what", "why", "how", "did", "does", "was",
    "were", "are", "has", "have", "had", "its", "his", "her", "their", "this",
    "that", "these", "those", "from", "into", "onto", "about", "after",
    "before", "over", "under", "will", "would", "could", "should", "can",
    "company", "companies", "stock", "shares", "tell", "show", "give",
    "there", "which", "when", "where", "who", "whom", "not", "but", "any",
    "all", "out", "off", "per", "than", "then", "them", "they", "you",
}


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _digest(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return cleaned or f"node-{_digest(value)}"


def _clean_sentiment(value: Any) -> str:
    if isinstance(value, str):
        candidate = value.strip().capitalize()
        if candidate in SENTIMENT_SCORE:
            return candidate
    return "Neutral"


def _first_sentence(text: str, limit: int = 260) -> str:
    if not text:
        return ""

    collapsed = " ".join(text.split())
    parts = re.split(r"(?<=[.!?])\s+", collapsed, maxsplit=1)
    sentence = parts[0] if parts else collapsed

    if len(sentence) > limit:
        sentence = sentence[:limit].rstrip() + "…"

    return sentence


def _impact(sentiment: str, signal_count: int, days_ago: int) -> int:
    """Deterministic 0-100 heuristic: sentiment, breadth and recency."""

    recency = max(0, 14 - days_ago) * 1.8
    value = IMPACT_BASE[sentiment] + min(signal_count, 4) * 6 + recency
    return max(12, min(99, round(value)))


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[\w₹%-]+", (text or "").casefold())
    return {word.strip("-") for word in words if len(word) > 2 and word not in STOPWORDS}


# --------------------------------------------------------------------------- #
# Knowledge graph loading
# --------------------------------------------------------------------------- #


def load_graphs() -> list[dict]:
    """Flatten every graph file into one list of graph dictionaries."""

    graphs: list[dict] = []

    if not GRAPH_DIR.exists():
        return graphs

    for path in sorted(GRAPH_DIR.glob("*.json")):
        try:
            payload = _read_json(path)
        except (OSError, json.JSONDecodeError):
            continue

        entries = payload.get("graphs") if isinstance(payload, dict) else None

        if not entries and isinstance(payload, dict) and "entities" in payload:
            entries = [payload]

        for graph in entries or []:
            if not isinstance(graph, dict):
                continue

            entities = [
                entity
                for entity in graph.get("entities", [])
                if isinstance(entity, dict) and entity.get("name")
            ]

            graphs.append(
                {
                    "file": path.name,
                    "graph_id": graph.get("graph_id") or f"kg_{_digest(path.name)}",
                    "sentiment": _clean_sentiment(graph.get("sentiment_label")),
                    "entities": entities,
                    "relations": [
                        relation
                        for relation in graph.get("relations", [])
                        if isinstance(relation, dict)
                    ],
                    "merged_text": (graph.get("merged_text") or "").strip(),
                    "source_documents": graph.get("source_documents") or [],
                }
            )

    return graphs


# --------------------------------------------------------------------------- #
# Event normalisation
# --------------------------------------------------------------------------- #


def _graph_language(graph: dict, fallback: str = "en") -> str:
    for document in graph.get("source_documents", []):
        if isinstance(document, dict):
            language = document.get("language")
            if language in LANGUAGE_LABELS:
                return language
    return fallback


def _graph_events(graphs: list[dict]) -> list[dict]:
    events: list[dict] = []

    for graph in graphs:
        days_ago = int(_digest(graph["graph_id"])[:2], 16) % 14
        language = _graph_language(graph)
        source = f"Knowledge graph · {graph['file']}"
        entity_names = [entity["name"] for entity in graph["entities"]]
        sentiment = graph["sentiment"]
        relations = graph["relations"]
        confidence = round(min(0.93, 0.58 + 0.045 * len(relations)), 2)
        stamp = _timestamp(days_ago, len(events))

        if not relations:
            if not graph["merged_text"]:
                continue

            events.append(
                {
                    "id": f"evt_{graph['graph_id']}_summary",
                    "title": _first_sentence(graph["merged_text"], 96),
                    "summary": _first_sentence(graph["merged_text"], 320),
                    "sentiment": sentiment,
                    "confidence": confidence,
                    "language": language,
                    "source": source,
                    "entities": entity_names[:8],
                    "timestamp": stamp,
                    "impact": _impact(sentiment, len(entity_names) // 2, days_ago),
                    "evidence": _first_sentence(graph["merged_text"], 320),
                }
            )
            continue

        for index, relation in enumerate(relations):
            source_entity = str(relation.get("source") or "Unknown")
            target_entity = str(relation.get("target") or "Unknown")
            relation_type = str(
                relation.get("type") or relation.get("relation") or "related to"
            )
            evidence = str(relation.get("evidence") or "").strip()

            attended = [source_entity, target_entity]

            for name in entity_names:
                if len(attended) >= 4:
                    break
                if name not in attended:
                    attended.append(name)

            events.append(
                {
                    "id": f"evt_{graph['graph_id']}_{index}",
                    "title": f"{source_entity} → {target_entity}: {relation_type}",
                    "summary": evidence
                    or _first_sentence(graph["merged_text"], 320),
                    "sentiment": _clean_sentiment(
                        relation.get("sentiment") or sentiment
                    ),
                    "confidence": confidence,
                    "language": language,
                    "source": source,
                    "entities": attended,
                    "timestamp": _timestamp(days_ago, len(events)),
                    "impact": _impact(sentiment, len(entity_names), days_ago),
                    "evidence": evidence
                    or _first_sentence(graph["merged_text"], 320),
                }
            )

    return events


def _timestamp(days_ago: int, index: int) -> str:
    """Stable timestamp: a fixed clock time N days back."""

    moment = _now() - timedelta(days=days_ago)
    return moment.replace(
        hour=8 + (index * 3) % 12,
        minute=(index * 17) % 60,
        second=0,
        microsecond=0,
    ).isoformat()


def _seed_events() -> list[dict]:
    path = DEMO_DIR / "events.json"

    if not path.exists():
        return []

    events: list[dict] = []

    for index, seed in enumerate(_read_json(path)):
        if not isinstance(seed, dict) or not seed.get("title"):
            continue

        sentiment = _clean_sentiment(seed.get("sentiment"))
        days_ago = int(seed.get("days_ago") or 0)
        entities = [str(name) for name in seed.get("entities", []) if name]

        events.append(
            {
                "id": str(seed.get("id") or f"evt_seed_{index}"),
                "title": str(seed["title"]),
                "summary": str(seed.get("summary") or ""),
                "sentiment": sentiment,
                "confidence": round(float(seed.get("confidence") or 0.6), 2),
                "language": str(seed.get("language") or "en"),
                "source": str(seed.get("source") or "SignalRadar wires"),
                "entities": entities,
                "timestamp": _timestamp(days_ago, index),
                "impact": _impact(sentiment, len(entities) // 2, days_ago),
                "evidence": str(seed.get("evidence") or seed.get("summary") or ""),
            }
        )

    return events


def build_events() -> list[dict]:
    events = _seed_events() + _graph_events(load_graphs())
    events.sort(key=lambda event: event["timestamp"], reverse=True)
    return events


# --------------------------------------------------------------------------- #
# Aggregates
# --------------------------------------------------------------------------- #


def build_kpis(events: list[dict], graphs: list[dict]) -> dict:
    documents = sum(len(graph.get("source_documents", [])) for graph in graphs)
    languages = sorted({event["language"] for event in events})
    at_risk = [
        event
        for event in events
        if event["sentiment"] == "Bearish" and event["impact"] >= 65
    ]

    return {
        "articles": documents + len(events),
        "events": len(events),
        "watchlist_risk": len(at_risk),
        "languages": len(languages),
        "language_labels": [LANGUAGE_LABELS.get(code, code) for code in languages],
        "bearish_share": round(
            sum(1 for event in events if event["sentiment"] == "Bearish")
            / max(1, len(events)),
            2,
        ),
    }


def build_timeline(events: list[dict], window: int = 14) -> list[dict]:
    """14 day buckets. Quiet days are interpolated between filings."""

    today = _now().date()
    days = [today - timedelta(days=offset) for offset in range(window - 1, -1, -1)]

    by_day: dict[date, list[dict]] = {day: [] for day in days}

    for event in events:
        try:
            moment = datetime.fromisoformat(event["timestamp"])
        except ValueError:
            continue
        day = moment.date()
        if day in by_day:
            by_day[day].append(event)

    points: list[dict] = []
    raw: list[float | None] = []

    for day in days:
        day_events = by_day[day]
        if day_events:
            weighted = sum(
                SENTIMENT_SCORE[event["sentiment"]] * event["confidence"]
                for event in day_events
            ) / len(day_events)
            raw.append(round(50 + 50 * weighted, 1))
        else:
            raw.append(None)

        points.append(
            {
                "date": day.isoformat(),
                "label": day.strftime("%d %b"),
                "count": len(day_events),
                "event_ids": [event["id"] for event in day_events],
                "score": None,
            }
        )

    known = [index for index, value in enumerate(raw) if value is not None]

    for index, value in enumerate(raw):
        if value is not None:
            points[index]["score"] = value
            continue

        previous = max((i for i in known if i < index), default=None)
        following = min((i for i in known if i > index), default=None)

        if previous is None and following is None:
            points[index]["score"] = 50.0
        elif previous is None:
            points[index]["score"] = raw[following]
        elif following is None:
            points[index]["score"] = raw[previous]
        else:
            span = following - previous
            step = (raw[following] - raw[previous]) / span
            points[index]["score"] = round(raw[previous] + step * (index - previous), 1)

    return points


def build_graph_payload(events: list[dict], graphs: list[dict]) -> dict:
    nodes: dict[str, dict] = {}
    links: dict[tuple[str, str, str], dict] = {}
    degree: dict[str, int] = {}

    def ensure_node(
        name: str,
        node_type: str = "Entity",
        sentiment: str = "Neutral",
    ) -> str:
        node_id = _slug(name)
        node = nodes.get(node_id)

        if node is None:
            node = {
                "id": node_id,
                "label": name,
                "type": node_type,
                "sentiment": sentiment,
                "mentions": 0,
                "weight": 1,
            }
            nodes[node_id] = node
        else:
            node["mentions"] += 1

        degree.setdefault(node_id, 0)
        return node_id

    for graph in graphs:
        for entity in graph["entities"]:
            ensure_node(
                str(entity["name"]),
                str(entity.get("type") or "Entity").capitalize(),
                _clean_sentiment(entity.get("sentiment") or graph["sentiment"]),
            )

        for relation in graph["relations"]:
            if not relation.get("source") or not relation.get("target"):
                continue

            source_name = str(relation["source"])
            target_name = str(relation["target"])
            sentiment = _clean_sentiment(
                relation.get("sentiment") or graph["sentiment"]
            )

            source_id = ensure_node(source_name, "Entity", sentiment)
            target_id = ensure_node(target_name, "Entity", sentiment)

            key = (source_id, target_id, sentiment)

            if key in links:
                links[key]["weight"] += 1
                continue

            links[key] = {
                "id": f"{source_id}--{target_id}--{len(links)}",
                "source": source_id,
                "target": target_id,
                "relation": str(
                    relation.get("type") or relation.get("relation") or "related to"
                ),
                "sentiment": sentiment,
                "weight": 1,
            }

            degree[source_id] += 1
            degree[target_id] += 1

    # Events that mention the same entities create co-mention edges, so the
    # force graph stays connected even where the saved graphs are sparse.
    paired = {
        frozenset((link["source"], link["target"])) for link in links.values()
    }

    for event in events:
        names = [name for name in event["entities"] if name][:5]
        ids = [ensure_node(name, "Entity", event["sentiment"]) for name in names]

        for node_id in ids:
            nodes[node_id]["mentions"] += 1

        for first, second in zip(ids, ids[1:]):
            pair = frozenset((first, second))

            if first == second or pair in paired:
                continue

            paired.add(pair)
            links[(first, second, "Neutral")] = {
                "id": f"{first}--{second}--co",
                "source": first,
                "target": second,
                "relation": "co-mentioned",
                "sentiment": event["sentiment"],
                "weight": 1,
            }

            degree[first] = degree.get(first, 0) + 1
            degree[second] = degree.get(second, 0) + 1

    for node_id, node in nodes.items():
        node["weight"] = max(1, degree.get(node_id, 0) + node["mentions"])

    return {
        "nodes": sorted(nodes.values(), key=lambda node: node["weight"], reverse=True),
        "links": list(links.values()),
    }


def build_divergence() -> dict:
    path = DEMO_DIR / "divergence.json"

    if not path.exists():
        return {}

    payload = _read_json(path)
    variants = payload.get("variants") or []

    labels = [variant.get("sentiment") for variant in variants if variant]
    if labels:
        dominant_count = max(labels.count(label) for label in set(labels))
        agreement = dominant_count / len(labels)
        score = round(min(0.94, 0.16 + 0.82 * (1 - agreement)), 2)
    else:
        score = 0.0

    for variant in variants:
        variant["sentiment"] = _clean_sentiment(variant.get("sentiment"))

    return {
        "id": payload.get("id") or "divergence",
        "title": payload.get("title") or "Language divergence",
        "summary": payload.get("summary") or "",
        "note": payload.get("note") or "",
        "score": score,
        "agreement": round(1 - score, 2),
        "variants": variants,
    }


def build_dashboard() -> dict:
    graphs = load_graphs()
    events = build_events()

    return {
        "kpis": build_kpis(events, graphs),
        "events": events,
        "timeline": build_timeline(events),
        "divergence": build_divergence(),
        "generated_at": _now().isoformat(),
        "sources": {
            "graphs": len(graphs),
            "graph_files": sorted({graph["file"] for graph in graphs}),
        },
    }


# --------------------------------------------------------------------------- #
# Copilot retrieval: keyword overlap plus graph adjacency, no LLM
# --------------------------------------------------------------------------- #


def _neighbours(graph_payload: dict) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}

    for link in graph_payload.get("links", []):
        index.setdefault(link["source"], set()).add(link["target"])
        index.setdefault(link["target"], set()).add(link["source"])

    return index


def _insufficient(events: list[dict]) -> dict:
    sample = sorted({entity for event in events for entity in event["entities"]})[:5]

    return {
        "answer": (
            "Insufficient evidence in the indexed graph for that question. "
            "The radar currently covers "
            + ", ".join(sample[:3])
            + ". Try asking about one of those entities or their reported metrics."
        ),
        "citations": [],
        "confidence": 0.12,
        "entities": sample,
        "sentiment": "Neutral",
        "insufficient": True,
    }


def answer_query(query: str, events: list[dict], graph_payload: dict) -> dict:
    tokens = tokenize(query)

    if not tokens or not events:
        return _insufficient(events)

    neighbours = _neighbours(graph_payload)
    labels = {
        node["id"]: node["label"] for node in graph_payload.get("nodes", [])
    }

    scored: list[tuple[float, dict]] = []

    for event in events:
        fields = {
            "title": tokenize(event["title"]),
            "entities": tokenize(" ".join(event["entities"])),
            "evidence": tokenize(event["evidence"]),
            "summary": tokenize(event["summary"]),
        }

        score = sum(
            weight * len(tokens & fields[field])
            for field, weight in FIELD_WEIGHTS.items()
        )

        query_folded = query.casefold()

        # Hybrid signal: a query term that names a graph neighbour of this
        # event's entity counts as partial evidence.
        for name in event["entities"]:
            node_id = _slug(name)
            for neighbour_id in neighbours.get(node_id, set()):
                label = labels.get(neighbour_id, "").casefold()
                if label and label in query_folded:
                    score += 1.2
                    break

        if score > 0:
            scored.append((score, event))

    if not scored:
        return _insufficient(events)

    scored.sort(key=lambda pair: (pair[0], pair[1]["timestamp"]), reverse=True)
    top_score = scored[0][0]

    if top_score < 2.0:
        return _insufficient(events)

    best = scored[0][1]
    ceiling = scored[0][0]

    citations = []
    for score, event in scored[:4]:
        citations.append(
            {
                "id": event["id"],
                "title": event["title"],
                "snippet": _first_sentence(event["evidence"] or event["summary"], 220),
                "source": event["source"],
                "sentiment": event["sentiment"],
                "score": round(min(0.99, score / ceiling), 2),
            }
        )

    corroboration = len(citations) - 1
    answer_parts = [
        f"{best['title']}.",
        _first_sentence(best["evidence"] or best["summary"], 240),
    ]

    if corroboration:
        answer_parts.append(
            f"{corroboration} other filing"
            + ("s" if corroboration > 1 else "")
            + " in the radar cover the same thread."
        )

    entities: list[str] = []
    for _, event in scored[:3]:
        for name in event["entities"]:
            if name not in entities:
                entities.append(name)

    return {
        "answer": " ".join(part for part in answer_parts if part),
        "citations": citations,
        "confidence": round(min(0.96, 0.34 + 0.075 * top_score), 2),
        "entities": entities[:6],
        "sentiment": best["sentiment"],
        "insufficient": False,
    }
