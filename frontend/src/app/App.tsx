import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Languages,
  Network,
  Radar as RadarIcon,
  RefreshCw,
  Sparkles,
  WifiOff,
} from 'lucide-react'
import { loadDashboard } from '../lib/api.ts'
import { viewTransition } from '../lib/motion.ts'
import { relativeTime } from '../lib/format.ts'
import type { Dashboard, ViewKey } from '../lib/types.ts'
import { RadarView } from '../features/radar/RadarView.tsx'
import { GraphView } from '../features/graph/GraphView.tsx'
import { DivergenceView } from '../features/divergence/DivergenceView.tsx'
import { CopilotView } from '../features/copilot/CopilotView.tsx'

const NAV: { key: ViewKey; label: string; icon: typeof RadarIcon }[] = [
  { key: 'radar', label: 'Radar', icon: RadarIcon },
  { key: 'graph', label: 'Graph', icon: Network },
  { key: 'divergence', label: 'Divergence', icon: Languages },
  { key: 'copilot', label: 'Copilot', icon: Sparkles },
]

export default function App() {
  const [view, setView] = useState<ViewKey>('radar')
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [offline, setOffline] = useState(false)
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    let cancelled = false

    setLoading(true)

    loadDashboard()
      .then(result => {
        if (cancelled) return
        setDashboard(result.data)
        setOffline(result.offline)
        setLoading(false)
      })
      .catch(() => {
        if (cancelled) return
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [reloadToken])

  const refresh = useCallback(() => setReloadToken(token => token + 1), [])

  const active = NAV.find(item => item.key === view) ?? NAV[0]!

  return (
    <div className="shell">
      <nav className="rail" aria-label="Sections">
        <div className="rail-mark" aria-hidden="true">
          <RadarIcon size={19} strokeWidth={1.6} />
        </div>

        <div className="rail-nav">
          {NAV.map(item => {
            const Icon = item.icon
            return (
              <button
                key={item.key}
                type="button"
                className={`rail-item${view === item.key ? ' is-active' : ''}`}
                onClick={() => setView(item.key)}
                aria-current={view === item.key ? 'page' : undefined}
              >
                <Icon size={17} strokeWidth={1.7} />
                {item.label}
              </button>
            )
          })}
        </div>

        <div className="rail-foot">SIGNALRADAR</div>
      </nav>

      <div className="workspace">
        <header className="app-header">
          <div>
            <h1 className="app-title">
              Signal<em>Radar</em>
            </h1>
            <p className="app-subtitle">
              Multilingual financial event and risk radar. Every signal below is traceable to a
              filing in the knowledge graph.
            </p>
          </div>

          <div className="header-right">
            {offline ? (
              <span className="offline-pill" title="The demo API did not answer, showing a bundled snapshot.">
                <WifiOff size={12} strokeWidth={2} />
                Offline snapshot
              </span>
            ) : (
              <span className="pulse">
                <i className="pulse-dot" />
                Live
              </span>
            )}

            <span className="view-meta">
              {dashboard?.generated_at ? `Updated ${relativeTime(dashboard.generated_at)}` : 'Syncing'}
            </span>

            <button
              type="button"
              className="icon-btn"
              onClick={refresh}
              title="Refresh data"
              aria-label="Refresh data"
            >
              <RefreshCw size={15} strokeWidth={1.8} className={loading ? 'spin' : ''} />
            </button>
          </div>
        </header>

        <motion.div
          key={view}
          variants={viewTransition}
          initial="hidden"
          animate="show"
        >
            {view === 'radar' && (
              <RadarView data={dashboard} loading={loading} offline={offline} />
            )}

            {view === 'graph' && (
              <GraphView events={dashboard?.events ?? []} loading={loading} />
            )}

            {view === 'divergence' && (
              <DivergenceView divergence={dashboard?.divergence ?? null} loading={loading} />
            )}

            {view === 'copilot' && (
              <CopilotView
                events={dashboard?.events ?? []}
                offline={offline}
                loading={loading}
              />
            )}
        </motion.div>

        <footer className="divergence-foot">
          <span>
            {active.label} view · {dashboard?.kpis.events ?? 0} events
          </span>
          <span>
            Sources: {dashboard?.sources?.graph_files.join(', ') ?? 'knowledge_graphs/'}
          </span>
          <span>Research output, not investment advice.</span>
        </footer>
      </div>
    </div>
  )
}
