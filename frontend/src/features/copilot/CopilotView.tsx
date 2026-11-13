import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { CornerDownLeft, Send, Sparkles } from 'lucide-react'
import { SentimentChip } from '../../components/SentimentChip.tsx'
import { SkeletonBlock } from '../../components/States.tsx'
import { useToast } from '../../components/Toast.tsx'
import { askCopilot } from '../../lib/api.ts'
import { percent } from '../../lib/format.ts'
import type { CopilotAnswer, EventItem } from '../../lib/types.ts'

interface Message {
  id: number
  role: 'user' | 'assistant'
  text: string
  answer?: CopilotAnswer
}

let messageId = 1

function buildSuggestions(events: EventItem[]): string[] {
  const companies: string[] = []

  for (const event of events) {
    const company = event.entities[0]

    if (company && !companies.includes(company)) {
      companies.push(company)
    }

    if (companies.length >= 4) break
  }

  return companies.map(company => `What is driving ${company}?`)
}

export function CopilotView({
  events,
  offline,
  loading,
}: {
  events: EventItem[]
  offline: boolean
  loading: boolean
}) {
  const toast = useToast()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  const suggestions = useMemo(() => buildSuggestions(events), [events])

  useEffect(() => {
    setMessages([
      {
        id: messageId++,
        role: 'assistant',
        text: 'Ask about any entity, metric or filing in the graph. Answers are extractive: every claim carries a citation you can expand.',
      },
    ])
  }, [])

  useEffect(() => {
    const element = scrollRef.current

    if (element) {
      element.scrollTop = element.scrollHeight
    }
  }, [messages, busy])

  async function send(rawQuery: string) {
    const query = rawQuery.trim()

    if (!query || busy) {
      return
    }

    setMessages(current => [...current, { id: messageId++, role: 'user', text: query }])
    setInput('')
    setBusy(true)

    const started = performance.now()
    const result = await askCopilot(query)

    // Keep the typing indicator visible long enough to read.
    const elapsed = performance.now() - started
    await new Promise(resolve => window.setTimeout(resolve, Math.max(0, 380 - elapsed)))

    if (result.offline && !offline) {
      toast('Backend unavailable — answered from the bundled snapshot')
    }

    setMessages(current => [
      ...current,
      {
        id: messageId++,
        role: 'assistant',
        text: result.data.answer,
        answer: result.data,
      },
    ])
    setBusy(false)
  }

  const entities = useMemo(
    () => Array.from(new Set(events.flatMap(event => event.entities))).slice(0, 12),
    [events],
  )

  return (
    <section>
      <div className="view-head">
        <div>
          <h2 className="view-title">Graph copilot</h2>
          <p className="view-desc">
            Keyword retrieval over the normalised events, expanded by graph adjacency. No language
            model, so it answers instantly and never invents a number.
          </p>
        </div>

        <div className="view-meta">{offline ? 'snapshot' : 'live'} · extractive</div>
      </div>

      <div className="copilot-shell">
        <div className="card chat-card">
          <div className="chat-scroll" ref={scrollRef}>
            {messages.map(message => (
              <motion.div
                key={message.id}
                className={`msg msg-${message.role}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, ease: 'easeOut' }}
              >
                <span className="msg-role">{message.role === 'user' ? 'You' : 'Copilot'}</span>

                <div
                  className={`bubble${message.answer?.insufficient ? ' is-insufficient' : ''}`}
                >
                  {message.text}

                  {message.answer && (
                    <>
                      <div className="answer-meta">
                        <SentimentChip sentiment={message.answer.sentiment} />
                        {message.answer.insufficient && (
                          <span className="tag" style={{ color: 'var(--warn)' }}>
                            insufficient evidence
                          </span>
                        )}
                      </div>

                      <div className="confidence-row">
                        <span>confidence</span>
                        <span className="conf-track">
                          <motion.span
                            initial={{ width: 0 }}
                            animate={{ width: percent(message.answer.confidence) }}
                            transition={{ duration: 0.6, ease: 'easeOut' }}
                            style={{ display: 'block', height: '100%', background: 'var(--accent)' }}
                          />
                        </span>
                        <span className="mono">{percent(message.answer.confidence)}</span>
                      </div>

                      {message.answer.citations.length > 0 && (
                        <div className="citations">
                          {message.answer.citations.map((citation, index) => (
                            <details className="citation" key={citation.id}>
                              <summary>
                                <span className="citation-index">{index + 1}</span>
                                <span className="citation-title">{citation.title}</span>
                                <span className="citation-score">
                                  {citation.score.toFixed(2)}
                                </span>
                              </summary>
                              <div className="citation-body">
                                {citation.snippet}
                                <div className="citation-source">
                                  {citation.source} · {citation.sentiment}
                                </div>
                              </div>
                            </details>
                          ))}
                        </div>
                      )}

                      {message.answer.entities.length > 0 && (
                        <div className="entity-chips">
                          {message.answer.entities.slice(0, 5).map(entity => (
                            <button
                              type="button"
                              key={entity}
                              className="suggestion"
                              onClick={() => setInput(`What is driving ${entity}?`)}
                            >
                              {entity}
                            </button>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </motion.div>
            ))}

            {busy && (
              <div className="msg msg-assistant">
                <span className="msg-role">Copilot</span>
                <div className="bubble" style={{ padding: 0 }}>
                  <div className="typing" aria-label="Searching the graph">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </div>
            )}
          </div>

          {suggestions.length > 0 && messages.length < 3 && (
            <div className="suggestions">
              {suggestions.map(suggestion => (
                <button
                  type="button"
                  key={suggestion}
                  className="suggestion"
                  onClick={() => void send(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          <form
            className="chat-form"
            onSubmit={event => {
              event.preventDefault()
              void send(input)
            }}
          >
            <input
              className="chat-input"
              value={input}
              onChange={event => setInput(event.target.value)}
              placeholder="Ask about an entity, metric or event…"
              aria-label="Ask the copilot"
            />
            <button
              type="submit"
              className="btn btn-accent"
              disabled={busy || input.trim().length === 0}
            >
              <Send size={13} strokeWidth={2} />
              Ask
            </button>
            <span className="graph-hint" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <CornerDownLeft size={11} strokeWidth={2} />
              enter
            </span>
          </form>
        </div>

        <aside className="side-stack">
          <div className="card context-card">
            <div className="eyebrow">Graph context</div>

            {loading ? (
              <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
                <SkeletonBlock height={12} />
                <SkeletonBlock height={12} width="70%" />
              </div>
            ) : (
              <>
                <div className="context-list">
                  <div className="context-row">
                    Events indexed <span className="mono">{events.length}</span>
                  </div>
                  <div className="context-row">
                    Entities{' '}
                    <span className="mono">
                      {new Set(events.flatMap(event => event.entities)).size}
                    </span>
                  </div>
                  <div className="context-row">
                    Retrieval <span>keyword + adjacency</span>
                  </div>
                </div>

                <div className="divider" />

                <div className="eyebrow">Try an entity</div>
                <div className="entity-chips">
                  {entities.slice(0, 8).map(entity => (
                    <button
                      type="button"
                      key={entity}
                      className="suggestion"
                      onClick={() => setInput(`What is driving ${entity}?`)}
                    >
                      {entity}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          <div className="card context-card">
            <div className="eyebrow">How it answers</div>
            <p className="muted" style={{ fontSize: 11.8, marginTop: 8, lineHeight: 1.6 }}>
              Query terms are matched against event titles, entities, summaries and evidence. Graph
              neighbours add a partial match, so a question about a metric still reaches the company
              it belongs to.
            </p>
            <p className="muted" style={{ fontSize: 11.8, marginTop: 8, lineHeight: 1.6 }}>
              If the best match is weak, the copilot says so instead of guessing.
            </p>
            <div className="entity-chips" style={{ marginTop: 12 }}>
              <span className="tag">
                <Sparkles size={11} strokeWidth={2} />
                no LLM
              </span>
            </div>
          </div>
        </aside>
      </div>
    </section>
  )
}
