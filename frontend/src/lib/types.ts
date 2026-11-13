export type Sentiment = 'Bullish' | 'Bearish' | 'Neutral'

export type LanguageCode = 'en' | 'hi' | 'te'

export interface EventItem {
  id: string
  title: string
  summary: string
  sentiment: Sentiment
  confidence: number
  language: string
  source: string
  entities: string[]
  timestamp: string
  impact: number
  evidence: string
}

export interface Kpis {
  articles: number
  events: number
  watchlist_risk: number
  languages: number
  language_labels?: string[]
  bearish_share?: number
}

export interface TimelinePoint {
  date: string
  label: string
  score: number | null
  count: number
  event_ids: string[]
}

export interface DivergenceHighlight {
  text: string
  sentiment: Sentiment
}

export interface DivergenceVariant {
  language: string
  label: string
  source: string
  sentiment: Sentiment
  confidence: number
  text: string
  highlights: DivergenceHighlight[]
}

export interface Divergence {
  id: string
  title: string
  summary: string
  note: string
  score: number
  agreement: number
  variants: DivergenceVariant[]
}

export interface Dashboard {
  kpis: Kpis
  events: EventItem[]
  timeline: TimelinePoint[]
  divergence: Divergence
  generated_at?: string
  sources?: { graphs: number; graph_files: string[] }
}

export interface GraphNode {
  id: string
  label: string
  type: string
  sentiment: Sentiment
  mentions: number
  weight: number
  x?: number
  y?: number
}

export interface GraphLink {
  id: string
  source: string | GraphNode
  target: string | GraphNode
  relation: string
  sentiment: Sentiment
  weight: number
}

export interface DemoGraph {
  nodes: GraphNode[]
  links: GraphLink[]
}

export interface Citation {
  id: string
  title: string
  snippet: string
  source: string
  sentiment: Sentiment
  score: number
}

export interface CopilotAnswer {
  answer: string
  citations: Citation[]
  confidence: number
  entities: string[]
  sentiment: Sentiment
  insufficient?: boolean
}

export type ViewKey = 'radar' | 'graph' | 'divergence' | 'copilot'
