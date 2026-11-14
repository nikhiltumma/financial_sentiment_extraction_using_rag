import { fallbackAnswer, fallbackDashboard, fallbackGraph } from "./fallback.ts";

const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function req(path: string, options: RequestInit = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${path} -> ${res.status}: ${body}`);
  }
  return res;
}

export const api = {
  get: <T>(path: string) => req<T>(path).then((r) => r.json()),

  post: <T>(path: string, body: unknown) =>
    req<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    }).then((r) => r.json()),

  upload: (path: string, file: File, format = "json") => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("format", format);
    return fetch(`${BASE}${path}`, { method: "POST", body: fd }).then((r) => r.json());
  },

  uploadRaw: (path: string, events: unknown[]) => {
    // Plain JSON body upload for the /ingest endpoint
    return fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events }),
    }).then((r) => r.json());
  },

  ingest: (events: unknown[]) =>
    api.post("/ingest", { events }),

  export: (format = "json") =>
    fetch(`${BASE}/export?format=${format}`).then((r) => {
      const url = r.url;
      return fetch(url).then((res) => res.blob()).then((b) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(b);
        const ext = format === "csv" ? "csv" : format === "xlsx" ? "xlsx" : "json";
        a.download = `signalradar_events_${new Date().toISOString().slice(0, 10)}.${ext}`;
        a.click();
        URL.revokeObjectURL(a.href);
        return a;
      });
    }),
};

export function liveDataStatus() {
  return api.get("/demo/data/artifacts");
}

export function listEvents() {
  return api.get("/demo/data/events");
}

export function clearUploads() {
  return api.get("/data/clear-uploads");
}

export async function loadDashboard() {
  let data: any
  let offline = false

  try {
    const eventsRes = await api.get("/demo/data/events")
    const events = Array.isArray(eventsRes) ? eventsRes : []

    const artifacts = await api.get("/demo/data/artifacts")
    const uploadedFiles = Array.isArray(artifacts?.uploaded_files)
      ? artifacts.uploaded_files
      : []

    const KPIS = {
      articles: events.length,
      events: events.length,
      watchlist_risk: events.filter(
        (e: any) => (e.sentiment === "Bearish" || e.sentiment === "bearish") &&
        typeof e.impact === "number" &&
        e.impact >= 65,
      ).length,
      languages: new Set(
        (events as any[]).map((e: any) => e.language),
      ).size,
      language_labels: [
        "English", "Hindi", "Telugu", "Bengali", "Tamil", "Marathi",
        "Gujarati", "Kannada", "Malayalam", "Urdu",
        "Spanish", "French", "German", "Arabic",
        "Portuguese", "Japanese", "Korean", "Chinese",
      ],
    }

    data = {
      kpis: KPIS,
      events: events.map(
        (e: any) =>
          ({
            id: e.id ?? "",
            title: e.title ?? "",
            summary: e.summary ?? "",
            sentiment: (e.sentiment ??
              "Neutral") as
              | "Bullish"
              | "Bearish"
              | "Neutral",
            confidence: typeof e.confidence === "number"
              ? e.confidence
              : 0.5,
            language: String(e.language ?? "en"),
            source: e.source ?? "",
            entities: Array.isArray(e.entities)
              ? e.entities
              : [],
            timestamp: e.timestamp ?? new Date().toISOString(),
            impact: typeof e.impact === "number"
              ? e.impact
              : 50,
            evidence: e.text ?? e.summary ?? "",
          } as any),
      ),
      timeline: [],
      divergence: null as any,
      generated_at: new Date().toISOString(),
      sources: { graphs: 0, graph_files: [] },
    }
  } catch (err) {
    offline = true
    const fb = fallbackDashboard()
    data = fb
  }

  return { data, offline }
}

export async function loadGraph() {
  let data: any
  let offline = false

  try {
    const res = await api.get("/graph")
    data = res as any
  } catch (err) {
    offline = true
    data = fallbackGraph()
  }

  return { data, offline }
}

export async function askCopilot(query: string) {
  let data: any
  let offline = false

  try {
    const res = await api.post("/copilot", { query })
    data = res as any
  } catch (err) {
    offline = true
    data = fallbackAnswer(query)
  }

  return { data, offline }
}
