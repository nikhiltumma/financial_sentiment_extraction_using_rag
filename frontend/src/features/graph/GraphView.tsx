import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { Info, X } from 'lucide-react'
import { SentimentChip } from '../../components/SentimentChip.tsx'
import { EmptyState, SkeletonBlock } from '../../components/States.tsx'
import { loadGraph } from '../../lib/api.ts'
import { sentimentTone } from '../../lib/format.ts'
import type { DemoGraph, EventItem, GraphLink, GraphNode, Sentiment } from '../../lib/types.ts'

interface ForceNode extends GraphNode {
  x?: number
  y?: number
}

const NODE_COLORS: Record<Sentiment, string> = {
  Bullish: '#34D399',
  Bearish: '#FB7185',
  Neutral: '#8A94A6',
}

function linkEnd(value: string | GraphNode): string {
  return typeof value === 'string' ? value : value.id
}

export function GraphView({ events, loading }: { events: EventItem[]; loading: boolean }) {
  const [graph, setGraph] = useState<DemoGraph | null>(null)
  const [offline, setOffline] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const [hovered, setHovered] = useState<string | null>(null)
  const [size, setSize] = useState({ width: 720, height: 520 })
  const wrapRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    let cancelled = false

    loadGraph().then(result => {
      if (cancelled) return
      setGraph(result.data)
      setOffline(result.offline)
    })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const element = wrapRef.current

    if (!element) return

    const observer = new ResizeObserver(entries => {
      const box = entries[0]?.contentRect

      if (box && box.width > 0) {
        setSize({ width: box.width, height: box.height })
      }
    })

    observer.observe(element)

    return () => observer.disconnect()
  }, [graph])

  const active = graph?.nodes.find(node => node.id === selected) ?? null

  const relations = useMemo(() => {
    if (!graph || !active) return []

    return graph.links.filter(
      link => linkEnd(link.source) === active.id || linkEnd(link.target) === active.id,
    )
  }, [graph, active])

  const evidence = useMemo(() => {
    if (!active) return []

    return events
      .filter(event => event.entities.includes(active.label))
      .sort((a, b) => b.impact - a.impact)
      .slice(0, 3)
  }, [events, active])

  const nodeById = useMemo(() => {
    const index = new Map<string, GraphNode>()

    for (const node of graph?.nodes ?? []) {
      index.set(node.id, node)
    }

    return index
  }, [graph])

  const drawNode = useCallback(
    (rawNode: object, ctx: CanvasRenderingContext2D, scale: number) => {
      const node = rawNode as ForceNode
      const x = node.x ?? 0
      const y = node.y ?? 0
      const radius = 2.2 + Math.min(9, Math.sqrt(node.weight) * 1.6)
      const color = NODE_COLORS[node.sentiment] ?? NODE_COLORS.Neutral
      const isSelected = node.id === selected
      const isHovered = node.id === hovered

      ctx.beginPath()
      ctx.arc(x, y, radius, 0, Math.PI * 2)
      ctx.fillStyle = color
      ctx.globalAlpha = isSelected || isHovered ? 1 : 0.82
      ctx.fill()
      ctx.globalAlpha = 1

      if (isSelected || isHovered) {
        ctx.beginPath()
        ctx.arc(x, y, radius + 3.5, 0, Math.PI * 2)
        ctx.strokeStyle = isSelected ? '#5EEAD4' : 'rgba(232,237,245,0.55)'
        ctx.lineWidth = 1.4 / scale
        ctx.stroke()
      }

      const showLabel = scale > 1.35 || isSelected || isHovered

      if (showLabel) {
        const fontSize = Math.max(1.6, 10.5 / scale)
        ctx.font = `${fontSize}px Inter, system-ui, sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        ctx.fillStyle = isSelected ? '#FFFFFF' : 'rgba(232,237,245,0.72)'
        const label = node.label.length > 26 ? `${node.label.slice(0, 25)}…` : node.label
        ctx.fillText(label, x, y + radius + 4 / scale)
      }

      if (isHovered && !isSelected) {
        const label = `${node.label} · ${node.sentiment.toLowerCase()}`
        const fontSize = Math.max(2, 11 / scale)
        ctx.font = `${fontSize}px Inter, system-ui, sans-serif`
        const padding = 5 / scale
        const width = ctx.measureText(label).width + padding * 2
        const height = fontSize + padding * 2
        const boxX = x - width / 2
        const boxY = y - radius - height - 6 / scale

        ctx.beginPath()
        ctx.roundRect(boxX, boxY, width, height, 4 / scale)
        ctx.fillStyle = 'rgba(20,26,36,0.96)'
        ctx.fill()
        ctx.strokeStyle = 'rgba(255,255,255,0.16)'
        ctx.lineWidth = 1 / scale
        ctx.stroke()

        ctx.fillStyle = '#E8EDF5'
        ctx.textBaseline = 'middle'
        ctx.fillText(label, x, boxY + height / 2)
      }
    },
    [hovered, selected],
  )

  const paintPointer = useCallback((rawNode: object, color: string, ctx: CanvasRenderingContext2D) => {
    const node = rawNode as ForceNode
    const radius = 4 + Math.min(9, Math.sqrt(node.weight) * 1.6)

    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(node.x ?? 0, node.y ?? 0, radius, 0, Math.PI * 2)
    ctx.fill()
  }, [])

  if (loading || !graph) {
    return (
      <section>
        <div className="view-head">
          <div>
            <h2 className="view-title">Knowledge graph</h2>
            <p className="view-desc">Entities and relations from every indexed filing.</p>
          </div>
        </div>
        <div className="graph-layout">
          <SkeletonBlock height={520} radius={16} />
          <SkeletonBlock height={520} radius={16} />
        </div>
      </section>
    )
  }

  if (graph.nodes.length === 0) {
    return (
      <section>
        <div className="view-head">
          <div>
            <h2 className="view-title">Knowledge graph</h2>
          </div>
        </div>
        <div className="card">
          <EmptyState
            title="The graph is empty"
            description="Build a knowledge graph from the analysis API, then reload this view."
          />
        </div>
      </section>
    )
  }

  return (
    <section>
      <div className="view-head">
        <div>
          <h2 className="view-title">Knowledge graph</h2>
          <p className="view-desc">
            {graph.nodes.length} entities and {graph.links.length} relations. Select a node to read
            the relations and the evidence behind them.
          </p>
        </div>

        <div className="view-meta">
          {offline ? 'snapshot' : 'live'} · click a node
        </div>
      </div>

      <div className="graph-layout">
        <div className="graph-canvas" ref={wrapRef}>
          <ForceGraph2D
            graphData={graph}
            width={size.width}
            height={size.height}
            backgroundColor="rgba(0,0,0,0)"
            nodeRelSize={4}
            nodeVal={node => (node as ForceNode).weight}
            nodeColor={node => NODE_COLORS[(node as ForceNode).sentiment] ?? NODE_COLORS.Neutral}
            nodeCanvasObject={drawNode}
            nodePointerAreaPaint={paintPointer}
            linkColor={link =>
              (link as GraphLink).relation === 'co-mentioned'
                ? 'rgba(255,255,255,0.1)'
                : 'rgba(94,234,212,0.42)'
            }
            linkWidth={link => ((link as GraphLink).relation === 'co-mentioned' ? 0.6 : 1.2)}
            linkDirectionalParticles={1}
            linkDirectionalParticleWidth={1.1}
            linkDirectionalParticleSpeed={0.004}
            linkDirectionalParticleColor={() => 'rgba(94,234,212,0.8)'}
            onNodeClick={node => setSelected((node as ForceNode).id)}
            onNodeHover={node => setHovered(node ? (node as ForceNode).id : null)}
            onBackgroundClick={() => setSelected(null)}
            cooldownTicks={90}
            d3AlphaDecay={0.028}
          />

          <div className="graph-hud">
            <div className="graph-legend">
              <span>
                <i style={{ background: NODE_COLORS.Bullish }} /> Bullish
              </span>
              <span>
                <i style={{ background: NODE_COLORS.Bearish }} /> Bearish
              </span>
              <span>
                <i style={{ background: NODE_COLORS.Neutral }} /> Neutral
              </span>
            </div>
            <span className="graph-hint">drag to pan · scroll to zoom</span>
          </div>
        </div>

        <aside className="card graph-panel">
          {active ? (
            <>
              <div className="panel-head-row">
                <div>
                  <div className="eyebrow">Selected entity</div>
                  <h3 className="node-title">{active.label}</h3>
                </div>
                <button
                  type="button"
                  className="icon-btn"
                  onClick={() => setSelected(null)}
                  aria-label="Clear selection"
                >
                  <X size={14} strokeWidth={2} />
                </button>
              </div>

              <div className="node-meta">
                <SentimentChip sentiment={active.sentiment} />
                <span className="tag">{active.type}</span>
                <span className="tag">{active.mentions} mentions</span>
                <span className="tag">{relations.length} relations</span>
              </div>

              <div>
                <div className="eyebrow">Relations</div>
                <div className="relation-list" style={{ marginTop: 8 }}>
                  {relations.length === 0 && (
                    <p className="muted" style={{ fontSize: 12 }}>
                      No graph relations for this entity yet.
                    </p>
                  )}

                  {relations.map(link => {
                    const fromId = linkEnd(link.source)
                    const toId = linkEnd(link.target)
                    const otherId = fromId === active.id ? toId : fromId

                    return (
                      <div className="relation-row" key={link.id}>
                        <div className="relation-path">
                          <span>{active.label}</span>
                          <span className="relation-arrow">→</span>
                          <span className="relation-type">{link.relation}</span>
                          <span className="relation-arrow">→</span>
                          <span>{nodeById.get(otherId)?.label ?? otherId}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              <div>
                <div className="eyebrow">Evidence</div>
                <div className="relation-list" style={{ marginTop: 8 }}>
                  {evidence.length === 0 && (
                    <p className="muted" style={{ fontSize: 12 }}>
                      No filing in the radar quotes this entity.
                    </p>
                  )}

                  {evidence.map(event => (
                    <div className="relation-row" key={event.id}>
                      <div style={{ fontSize: 11.5, color: 'var(--text)' }}>{event.title}</div>
                      <p className="evidence-quote">{event.evidence}</p>
                      <div className="lang-foot" style={{ marginTop: 7, paddingTop: 7 }}>
                        <span>{event.source}</span>
                        <span className={`sentiment-${sentimentTone(event.sentiment)}`}>
                          {event.sentiment}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <>
              <div>
                <div className="eyebrow">Graph overview</div>
                <h3 className="node-title">Pick an entity</h3>
                <p className="muted" style={{ fontSize: 12.5, marginTop: 6 }}>
                  Nodes are coloured by sentiment and sized by how often they appear across filings.
                </p>
              </div>

              <div className="relation-list">
                {graph.nodes.slice(0, 8).map(node => (
                  <button
                    type="button"
                    key={node.id}
                    className="relation-row"
                    style={{
                      textAlign: 'left',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                    }}
                    onClick={() => setSelected(node.id)}
                  >
                    <span
                      style={{
                        width: 7,
                        height: 7,
                        borderRadius: '50%',
                        background: NODE_COLORS[node.sentiment],
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ flex: 1, minWidth: 0 }}>{node.label}</span>
                    <span className="mono dim" style={{ fontSize: 10.5 }}>
                      {node.weight}
                    </span>
                  </button>
                ))}
              </div>

              <p className="muted" style={{ fontSize: 11.5, display: 'flex', gap: 6 }}>
                <Info size={13} strokeWidth={1.8} style={{ flexShrink: 0, marginTop: 2 }} />
                Relations come from the saved knowledge graphs; co-mention edges link entities that
                appear in the same event.
              </p>
            </>
          )}
        </aside>
      </div>
    </section>
  )
}
