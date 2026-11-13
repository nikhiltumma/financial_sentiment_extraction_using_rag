import { useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Search, Star } from 'lucide-react'
import { CountUp } from '../../components/CountUp.tsx'
import { EmptyState, EventSkeleton, SkeletonBlock } from '../../components/States.tsx'
import { stagger } from '../../lib/motion.ts'
import { sentimentTone } from '../../lib/format.ts'
import { useWatchlist } from '../../lib/watchlist.ts'
import type { Dashboard, Sentiment } from '../../lib/types.ts'
import { EventCard } from './EventCard.tsx'
import { PulseChart } from './PulseChart.tsx'

const SENTIMENT_FILTERS: (Sentiment | 'All')[] = ['All', 'Bullish', 'Bearish', 'Neutral']

const LANGUAGES = [
  { value: 'all', label: 'All languages' },
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'Hindi' },
  { value: 'te', label: 'Telugu' },
]

const TONE_COLORS: Record<string, string> = {
  bullish: 'var(--pos)',
  bearish: 'var(--neg)',
  neutral: 'var(--muted)',
}

export function RadarView({
  data,
  loading,
  offline,
}: {
  data: Dashboard | null
  loading: boolean
  offline: boolean
}) {
  const [sentiment, setSentiment] = useState<Sentiment | 'All'>('All')
  const [language, setLanguage] = useState('all')
  const [search, setSearch] = useState('')
  const watchlist = useWatchlist()

  const events = data?.events ?? []

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase()

    return events
      .filter(event => {
        if (sentiment !== 'All' && event.sentiment !== sentiment) return false
        if (language !== 'all' && event.language !== language) return false
        if (!needle) return true

        const haystack = [event.title, event.summary, event.entities.join(' '), event.source]
          .join(' ')
          .toLowerCase()

        return haystack.includes(needle)
      })
      .sort((a, b) => b.impact - a.impact)
  }, [events, sentiment, language, search])

  const mix = useMemo(() => {
    const counts = { Bullish: 0, Bearish: 0, Neutral: 0 }

    for (const event of events) {
      counts[event.sentiment] += 1
    }

    return counts
  }, [events])

  const kpis = data?.kpis

  return (
    <section>
      <div className="view-head">
        <div>
          <h2 className="view-title">Event radar</h2>
          <p className="view-desc">
            Ranked by impact: sentiment strength, how many graph relations support the event, and how
            recent it is.
          </p>
        </div>

        <div className="view-meta">
          {offline ? 'snapshot' : 'live'} · {filtered.length} shown
        </div>
      </div>

      <div className="kpi-strip">
        {[
          {
            label: 'Articles analysed',
            value: kpis?.articles ?? 0,
            foot: 'PDF, DOCX, CSV and wire text',
          },
          {
            label: 'Events ranked',
            value: kpis?.events ?? 0,
            foot: 'normalised graph signals',
          },
          {
            label: 'Watchlist risk',
            value: kpis?.watchlist_risk ?? 0,
            foot: 'bearish · impact ≥ 65',
          },
          {
            label: 'Languages',
            value: kpis?.languages ?? 0,
            foot: kpis?.language_labels?.join(' · ') ?? 'EN · HI · TE',
          },
        ].map(tile => (
          <div className="card kpi" key={tile.label}>
            <div className="kpi-label">{tile.label}</div>
            <div className="kpi-value">
              {loading ? <SkeletonBlock height={30} width={54} /> : <CountUp value={tile.value} />}
            </div>
            <div className="kpi-foot">{tile.foot}</div>
          </div>
        ))}
      </div>

      <div className="filter-bar">
        <div className="filter-group" role="group" aria-label="Filter by sentiment">
          {SENTIMENT_FILTERS.map(option => (
            <button
              key={option}
              type="button"
              className={[
                'filter-chip',
                option !== 'All' ? `chip-${sentimentTone(option)}` : '',
                sentiment === option ? 'is-active' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              onClick={() => setSentiment(option)}
            >
              {option}
            </button>
          ))}
        </div>

        <select
          className="select"
          value={language}
          onChange={event => setLanguage(event.target.value)}
          aria-label="Filter by language"
        >
          {LANGUAGES.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <div className="search-wrap">
          <Search size={13} strokeWidth={1.9} />
          <input
            className="input"
            value={search}
            onChange={event => setSearch(event.target.value)}
            placeholder="Search entity, metric or source…"
            aria-label="Search events"
          />
        </div>

        {watchlist.ids.length > 0 && (
          <span className="tag" title="Saved on this device">
            <Star size={11} strokeWidth={2} fill="currentColor" />
            {watchlist.ids.length} watching
          </span>
        )}

        <span className="result-count">{filtered.length} / {events.length}</span>
      </div>

      <div className="radar-grid">
        <div>
          <motion.div className="event-list" variants={stagger} initial="hidden" animate="show">
            {loading &&
              [0, 1, 2].map(index => <EventSkeleton key={`skeleton-${index}`} />)}

            {!loading &&
              filtered.map(event => (
                <EventCard
                  key={event.id}
                  event={event}
                  watched={watchlist.has(event.id)}
                  onToggleWatch={watchlist.toggle}
                />
              ))}
          </motion.div>

          {!loading && filtered.length === 0 && (
            <div className="card">
              <EmptyState
                title="No events match these filters"
                description="Widen the sentiment or language filter, or clear the search to see the full radar."
                action={
                  <button
                    type="button"
                    className="btn"
                    onClick={() => {
                      setSentiment('All')
                      setLanguage('all')
                      setSearch('')
                    }}
                  >
                    Reset filters
                  </button>
                }
              />
            </div>
          )}
        </div>

        <div className="side-stack">
          <div className="card side-card">
            <div className="side-head">
              <div>
                <div className="side-title">Sentiment pulse</div>
                <div className="side-desc">14 days, confidence-weighted</div>
              </div>
              <span className="eyebrow">0–100</span>
            </div>

            {loading || !data ? (
              <SkeletonBlock height={186} radius={10} />
            ) : (
              <PulseChart timeline={data.timeline} />
            )}

            <div className="chart-legend">
              <span>
                <i style={{ background: 'var(--accent)' }} /> daily score
              </span>
              <span>
                <i style={{ background: 'rgba(255,255,255,0.3)' }} /> neutral 50
              </span>
            </div>
          </div>

          <div className="card side-card">
            <div className="side-head">
              <div>
                <div className="side-title">Sentiment mix</div>
                <div className="side-desc">Across all ranked events</div>
              </div>
            </div>

            <div className="mix-bar">
              {(['Bullish', 'Neutral', 'Bearish'] as Sentiment[]).map(name => {
                const share = events.length ? (mix[name] / events.length) * 100 : 0
                return (
                  <span
                    key={name}
                    style={{
                      width: `${share}%`,
                      background: TONE_COLORS[sentimentTone(name)],
                      opacity: 0.85,
                    }}
                  />
                )
              })}
            </div>

            <div className="mix-list">
              {(['Bullish', 'Neutral', 'Bearish'] as Sentiment[]).map(name => (
                <div className="mix-row" key={name}>
                  <i
                    className="mix-swatch"
                    style={{ background: TONE_COLORS[sentimentTone(name)] }}
                  />
                  {name}
                  <span className="mono">{mix[name]}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
