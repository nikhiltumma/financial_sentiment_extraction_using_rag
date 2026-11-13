import { fallbackAnswer, fallbackDashboard, fallbackGraph } from './fallback.ts'
import type { CopilotAnswer, Dashboard, DemoGraph } from './types.ts'

// Vite proxies /api to the FastAPI demo routes.
const BASE = '/api'
const TIMEOUT_MS = 4000

export interface Loaded<T> {
  data: T
  offline: boolean
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), TIMEOUT_MS)

  try {
    const response = await fetch(`${BASE}${path}`, { ...init, signal: controller.signal })

    if (!response.ok) {
      throw new Error(`${path} responded ${response.status}`)
    }

    return (await response.json()) as T
  } finally {
    window.clearTimeout(timer)
  }
}

export async function loadDashboard(): Promise<Loaded<Dashboard>> {
  try {
    return { data: await fetchJson<Dashboard>('/demo/dashboard'), offline: false }
  } catch {
    return { data: fallbackDashboard(), offline: true }
  }
}

export async function loadGraph(): Promise<Loaded<DemoGraph>> {
  try {
    return { data: await fetchJson<DemoGraph>('/demo/graph'), offline: false }
  } catch {
    return { data: fallbackGraph(), offline: true }
  }
}

export async function askCopilot(query: string): Promise<Loaded<CopilotAnswer>> {
  try {
    const data = await fetchJson<CopilotAnswer>('/demo/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    })

    return { data, offline: false }
  } catch {
    return { data: fallbackAnswer(query), offline: true }
  }
}
