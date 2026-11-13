import type {
  CopilotAnswer,
  Dashboard,
  DemoGraph,
  Divergence,
  EventItem,
  GraphLink,
  GraphNode,
  Sentiment,
  TimelinePoint,
} from './types.ts'

// Bundled snapshot used whenever the demo API cannot be reached, so a live
// demo never renders an empty screen. Mirrors the live payload shape exactly.

const HOUR = 3_600_000

interface Seed {
  id: string
  title: string
  summary: string
  sentiment: Sentiment
  confidence: number
  language: string
  source: string
  entities: string[]
  hoursAgo: number
}

const SEEDS: Seed[] = [
  {
    id: 'evt_meridian_tariff',
    title: 'Meridian Grid Infrastructure — FY26 guidance cut after tariff order deferred',
    summary:
      'The state regulator has still not notified the transmission tariff order. Meridian Grid trimmed FY26 revenue guidance to ₹8,900 crore and said margins stay under pressure until the order lands.',
    sentiment: 'Bearish',
    confidence: 0.84,
    language: 'en',
    source: 'Reuters · Energy Desk',
    entities: ['Meridian Grid Infrastructure', 'Transmission Tariff Order', 'FY26 Guidance'],
    hoursAgo: 2,
  },
  {
    id: 'evt_surya_cloud',
    title: 'Surya Technologies — cloud services revenue up 22% year on year',
    summary:
      'Cloud services carried the quarter while India enterprise deals stayed steady. Operating margin slipped to 14.2% from 17.8% as infrastructure spend rose ahead of new capacity.',
    sentiment: 'Bullish',
    confidence: 0.72,
    language: 'en',
    source: 'Exchange filing · Q4 results',
    entities: ['Surya Technologies Limited', 'Cloud Services', 'India', 'Operating Margin'],
    hoursAgo: 9,
  },
  {
    id: 'evt_abc_margin',
    title: 'ABC Technologies — Q4 revenue up 18%, operating margin contracts',
    summary:
      'Revenue reached ₹1,240 crore for the quarter, but operating margin fell to 14.2% from 17.8% on higher cloud infrastructure and hiring costs.',
    sentiment: 'Bearish',
    confidence: 0.77,
    language: 'en',
    source: 'Earnings call transcript',
    entities: ['ABC Technologies', 'Q4', 'Operating Margin', 'Revenue'],
    hoursAgo: 26,
  },
  {
    id: 'evt_nalanda_licence',
    title: 'Nalanda Finance — small finance bank licence granted',
    summary:
      'The regulator cleared the transition to a small finance bank, opening deposit-taking from the March quarter and lowering wholesale funding cost.',
    sentiment: 'Bullish',
    confidence: 0.81,
    language: 'en',
    source: 'Business Standard · Banking',
    entities: ['Nalanda Finance', 'Small Finance Bank Licence', 'Deposits'],
    hoursAgo: 40,
  },
  {
    id: 'evt_vantage_coal',
    title: 'Vantage Steel — coking coal costs squeeze EBITDA per tonne',
    summary:
      'Coking coal landed cost rose 11% quarter on quarter, pulling EBITDA per tonne down ₹1,850. Management expects the pressure to persist through the monsoon.',
    sentiment: 'Bearish',
    confidence: 0.74,
    language: 'hi',
    source: 'मिंट · इस्पात',
    entities: ['Vantage Steel', 'Coking Coal', 'EBITDA per Tonne'],
    hoursAgo: 55,
  },
  {
    id: 'evt_kalyani_ev',
    title: 'Kalyani Auto Components — ₹2,300 crore EV drivetrain order',
    summary:
      'The order covers drivetrain assemblies for two electric two-wheeler platforms and ramps from the September quarter across three plants in Tamil Nadu.',
    sentiment: 'Bullish',
    confidence: 0.86,
    language: 'en',
    source: 'Press release',
    entities: ['Kalyani Auto Components', 'EV Drivetrain', 'Tamil Nadu'],
    hoursAgo: 70,
  },
  {
    id: 'evt_deccan_usfda',
    title: 'Deccan Pharma Labs — Form 483 issued for Unit-II',
    summary:
      'The inspection closed with six observations covering sterility assurance and batch review. Unit-II contributes roughly a fifth of US generic revenue.',
    sentiment: 'Bearish',
    confidence: 0.69,
    language: 'te',
    source: 'ఫార్మా వార్తలు',
    entities: ['Deccan Pharma Labs', 'USFDA Form 483', 'Unit-II'],
    hoursAgo: 96,
  },
  {
    id: 'evt_orbit_upi',
    title: 'Orbit Payments — merchant additions steady, take rate flat',
    summary:
      'The company added 3.1 lakh merchants in the month while UPI take rate held at 0.42%. Management reiterated FY26 EBITDA breakeven.',
    sentiment: 'Neutral',
    confidence: 0.58,
    language: 'en',
    source: 'Investor update',
    entities: ['Orbit Payments', 'UPI Take Rate', 'Merchant Additions'],
    hoursAgo: 120,
  },
]

const IMPACT_BASE: Record<Sentiment, number> = { Bullish: 52, Bearish: 58, Neutral: 38 }

function buildEvents(): EventItem[] {
  return SEEDS.map(seed => ({
    id: seed.id,
    title: seed.title,
    summary: seed.summary,
    sentiment: seed.sentiment,
    confidence: seed.confidence,
    language: seed.language,
    source: seed.source,
    entities: seed.entities,
    timestamp: new Date(Date.now() - seed.hoursAgo * HOUR).toISOString(),
    impact: Math.max(
      12,
      Math.min(
        99,
        Math.round(
          IMPACT_BASE[seed.sentiment] +
            (seed.entities.length // breadth
              ? 6
              : 0) +
            Math.max(0, 120 - seed.hoursAgo) * 0.18 +
            seed.confidence * 8,
        ),
      ),
    ),
    evidence: seed.summary,
  })).sort((a, b) => b.timestamp.localeCompare(a.timestamp))
}

const TIMELINE_SCORES = [22, 61, 48, 74, 39, 82, 18, 44, 66, 30, 88, 52, 26, 71]
const TIMELINE_COUNTS = [2, 1, 0, 2, 1, 1, 0, 3, 1, 0, 2, 1, 1, 2]

function buildTimeline(): TimelinePoint[] {
  return TIMELINE_SCORES.map((score, index) => {
    const day = new Date()
    day.setDate(day.getDate() - (TIMELINE_SCORES.length - 1 - index))

    return {
      date: day.toISOString().slice(0, 10),
      label: day.toLocaleDateString(undefined, { day: '2-digit', month: 'short' }),
      score,
      count: TIMELINE_COUNTS[index] ?? 0,
      event_ids: [],
    }
  })
}

export const FALLBACK_DIVERGENCE: Divergence = {
  id: 'div_meridian_guidance',
  title: 'Meridian Grid trims FY26 guidance after tariff order deferred',
  summary:
    'The state regulator has not notified the transmission tariff order, so Meridian Grid Infrastructure cut its FY26 revenue guidance to ₹8,900 crore and flagged margin pressure. Coverage in the three languages frames the delay differently.',
  note: 'English and Telugu coverage treat the deferral as a margin problem; Hindi coverage calls it temporary and expects the order next quarter.',
  score: 0.43,
  agreement: 0.57,
  variants: [
    {
      language: 'en',
      label: 'English',
      source: 'Reuters · Energy Desk',
      sentiment: 'Bearish',
      confidence: 0.84,
      text: 'Meridian Grid Infrastructure cut its FY26 revenue guidance to ₹8,900 crore after the state regulator deferred the transmission tariff order. Management said margins will stay under pressure until the order is notified.',
      highlights: [
        { text: 'cut its FY26 revenue guidance', sentiment: 'Bearish' },
        { text: 'margins will stay under pressure', sentiment: 'Bearish' },
      ],
    },
    {
      language: 'hi',
      label: 'Hindi',
      source: 'वित्तीय समाचार · ऊर्जा',
      sentiment: 'Neutral',
      confidence: 0.61,
      text: 'मेरिडियन ग्रिड इंफ्रास्ट्रक्चर ने राज्य नियामक के ट्रांसमिशन टैरिफ आदेश को स्थगित किए जाने के बाद FY26 राजस्व अनुमान ₹8,900 करोड़ किया। कंपनी का कहना है कि स्थगन अस्थायी है और आदेश अगली तिमाही में जारी हो सकता है।',
      highlights: [{ text: 'स्थगन अस्थायी है', sentiment: 'Bullish' }],
    },
    {
      language: 'te',
      label: 'Telugu',
      source: 'ఆర్థిక సమాచారం · ఇన్ఫ్రా',
      sentiment: 'Bearish',
      confidence: 0.79,
      text: 'రాష్ట్ర నియంత్రణ సంస్థ ట్రాన్స్మిషన్ టారిఫ్ ఆదేశాన్ని వాయిదా వేయడంతో మెరిడియన్ గ్రిడ్ FY26 ఆదాయ అంచనాను ₹8,900 కోట్లకు తగ్గించింది. రుణ భారం పెరగడంతో మార్జిన్లపై ఒత్తిడి కొనసాగుతుంది.',
      highlights: [{ text: 'మార్జిన్లపై ఒత్తిడి', sentiment: 'Bearish' }],
    },
  ],
}

let cachedDashboard: Dashboard | null = null

export function fallbackDashboard(): Dashboard {
  if (cachedDashboard) {
    return cachedDashboard
  }

  const events = buildEvents()

  cachedDashboard = {
    kpis: {
      articles: 17,
      events: events.length,
      watchlist_risk: events.filter(event => event.sentiment === 'Bearish' && event.impact >= 65)
        .length,
      languages: 3,
      language_labels: ['English', 'Hindi', 'Telugu'],
      bearish_share: 0.42,
    },
    events,
    timeline: buildTimeline(),
    divergence: FALLBACK_DIVERGENCE,
    generated_at: new Date().toISOString(),
    sources: { graphs: 2, graph_files: ['financial_kg_550335d853.json', 'financial_kg_7a1a09f431.json'] },
  }

  return cachedDashboard
}

function slug(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}

export function fallbackGraph(): DemoGraph {
  const nodes = new Map<string, GraphNode>()
  const links: GraphLink[] = []
  const paired = new Set<string>()

  const ensure = (label: string, sentiment: Sentiment): GraphNode => {
    const id = slug(label)
    const existing = nodes.get(id)

    if (existing) {
      existing.mentions += 1
      return existing
    }

    const node: GraphNode = {
      id,
      label,
      type: 'Entity',
      sentiment,
      mentions: 1,
      weight: 1,
    }

    nodes.set(id, node)
    return node
  }

  for (const event of fallbackDashboard().events) {
    const ids = event.entities.map(name => ensure(name, event.sentiment))

    ids.forEach((node, index) => {
      if (index === 0) return

      const key = [ids[0]!.id, node.id].sort().join('|')

      if (paired.has(key)) return

      paired.add(key)
      links.push({
        id: `${key}-co`,
        source: ids[0]!.id,
        target: node.id,
        relation: 'co-mentioned',
        sentiment: event.sentiment,
        weight: 1,
      })
    })
  }

  for (const node of nodes.values()) {
    node.weight =
      1 +
      links.filter(link => link.source === node.id || link.target === node.id).length +
      node.mentions
  }

  return {
    nodes: [...nodes.values()].sort((a, b) => b.weight - a.weight),
    links,
  }
}

// Local keyword retrieval, mirroring the backend copilot when it is offline.
export function fallbackAnswer(query: string): CopilotAnswer {
  const words = query
    .toLowerCase()
    .split(/[^a-z0-9\u0900-\u097F\u0C00-\u0C7F]+/)
    .filter(word => word.length > 2)

  const scored = fallbackDashboard()
    .events.map(event => {
      const haystack = [
        event.title,
        event.summary,
        event.entities.join(' '),
        event.evidence,
      ]
        .join(' ')
        .toLowerCase()

      const score = words.reduce((total, word) => (haystack.includes(word) ? total + 1 : total), 0)
      return { event, score }
    })
    .filter(entry => entry.score > 0)
    .sort((a, b) => b.score - a.score)

  if (scored.length === 0) {
    return {
      answer:
        'Insufficient evidence in the indexed graph for that question. The snapshot covers Meridian Grid Infrastructure, Surya Technologies, ABC Technologies and six other names. Try asking about one of them.',
      citations: [],
      confidence: 0.12,
      entities: ['Meridian Grid Infrastructure', 'Surya Technologies Limited', 'ABC Technologies'],
      sentiment: 'Neutral',
      insufficient: true,
    }
  }

  const best = scored[0]!.event

  return {
    answer: `${best.title}. ${best.evidence}`,
    citations: scored.slice(0, 3).map(entry => ({
      id: entry.event.id,
      title: entry.event.title,
      snippet: entry.event.evidence,
      source: entry.event.source,
      sentiment: entry.event.sentiment,
      score: Math.min(0.99, entry.score / (scored[0]?.score ?? 1)),
    })),
    confidence: Math.min(0.9, 0.38 + 0.12 * scored[0]!.score),
    entities: best.entities,
    sentiment: best.sentiment,
    insufficient: false,
  }
}
