# financial_sentiment_extraction_using_rag

## SignalRadar — multilingual financial event & risk radar

SignalRadar turns the saved knowledge graphs in `knowledge_graphs/` into a demo-ready
product: a ranked event radar, a force-directed graph explorer, a cross-language
divergence view, and a graph copilot. The demo path is pure standard library — it never
touches Ollama, SentenceTransformers or FAISS — so the whole UI works with the model
server stopped.

### Run it

Two terminals, from the repo root.

Backend:

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Then open <http://localhost:5173>. The Vite dev server proxies `/api/*` to
`http://localhost:8000`, so no CORS configuration is needed in development.

> If the frontend runs but every panel shows "Offline snapshot", the backend is not
> answering on port 8000. Start it, then use the refresh button in the header.

### Demo API

| Endpoint | Returns |
| --- | --- |
| `GET /demo/dashboard` | KPIs, normalised events, a 14-day sentiment timeline and the curated divergence event |
| `GET /demo/graph` | `nodes` and `links` built from every entity and relation, plus co-mention edges |
| `POST /demo/query` | `{query}` → extractive answer, citations, confidence, related entities, sentiment |

Normalised event shape:

```json
{
  "id": "evt_abc_margin",
  "title": "ABC Technologies — Q4 revenue up 18%, operating margin contracts",
  "summary": "…",
  "sentiment": "Bearish",
  "confidence": 0.77,
  "language": "en",
  "source": "Earnings call transcript",
  "entities": ["ABC Technologies", "Q4"],
  "timestamp": "2026-11-11T09:17:00+00:00",
  "impact": 92,
  "evidence": "…"
}
```

### The four views

- **Radar** — KPI strip, sticky filter bar (sentiment, language, entity search), event
  cards ranked by impact, watchlist stars, and the 14-day sentiment pulse.
- **Graph** — force-directed canvas, node colour by sentiment, node size by weight, a
  detail panel with relations and the evidence quotes behind them, and a legend.
- **Divergence** — one event in English, Hindi and Telugu with per-language sentiment, a
  divergence score ring, and the disagreeing phrases highlighted.
- **Copilot** — chat over the graph with suggested questions, extractive answers,
  expandable citations, a confidence bar and related entities.

### Real vs seeded

- **From the knowledge graphs:** every relation becomes an event
  (`Source → Target: relation`), and graphs without relations become a one-line summary
  event. Entities and relations feed the graph view. Five of the sixteen demo events come
  from here today.
- **Curated seed data:** `backend/app/demo/events.json` (eleven realistic filings with
  `days_ago` offsets, so the radar always looks current) and
  `backend/app/demo/divergence.json` (the EN/HI/TE divergence example, using a fictional
  company). Nothing in `knowledge_graphs/` is modified.
- **Heuristics, not models:** `impact` is derived from sentiment, breadth and recency;
  the timeline score is confidence-weighted sentiment per day with quiet days
  interpolated; the copilot ranks events by keyword overlap plus graph adjacency. There
  is no language model involved, so answers are extractive and citations are real.

### When the backend is down

`frontend/src/lib/fallback.ts` bundles a snapshot of the same payload shapes. Every
request falls back to it after a 4 second timeout, the header switches to "Offline
snapshot", and all four views stay usable.

### Legacy API

The original analysis routes (`/analysis/*`, `/graph/generate`, `/ollama-status`) are
unchanged. They need the full ML stack, so `backend/app/main.py` registers them only when
they import successfully; the demo routes are always registered.

### Frontend structure

```
frontend/src
├── app/App.tsx              shell, rail navigation, data loading
├── components/              toast, sentiment chip, impact meter, count-up, states
├── features/radar           KPIs, filters, event cards, pulse chart
├── features/graph           force graph + detail panel
├── features/divergence      score ring + language columns
├── features/copilot         chat, citations, context panel
├── lib/                     API client, fallback snapshot, types, formatting
└── styles/                  design tokens, base, views
```

Design tokens live in `frontend/src/styles/tokens.css`: background `#07090D`, surface
`#0E1219`, mint accent `#5EEAD4`, positive `#34D399`, negative `#FB7185`, warning
`#FBBF24`, Instrument Serif for display, Inter for UI and JetBrains Mono for numbers.
