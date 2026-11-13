import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle } from 'lucide-react'
import { SentimentChip } from '../../components/SentimentChip.tsx'
import { SkeletonBlock } from '../../components/States.tsx'
import { languageFlag, percent, sentimentTone } from '../../lib/format.ts'
import type { Divergence, DivergenceHighlight, Sentiment } from '../../lib/types.ts'

interface Piece {
  text: string
  sentiment?: Sentiment
  highlight: boolean
}

function splitHighlights(text: string, highlights: DivergenceHighlight[]): Piece[] {
  const ranges: { start: number; end: number; sentiment: Sentiment }[] = []

  for (const highlight of highlights) {
    let index = text.indexOf(highlight.text)

    while (index !== -1) {
      ranges.push({ start: index, end: index + highlight.text.length, sentiment: highlight.sentiment })
      index = text.indexOf(highlight.text, index + highlight.text.length)
    }
  }

  ranges.sort((a, b) => a.start - b.start)

  const pieces: Piece[] = []
  let cursor = 0

  for (const range of ranges) {
    if (range.start < cursor) continue

    if (range.start > cursor) {
      pieces.push({ text: text.slice(cursor, range.start), highlight: false })
    }

    pieces.push({
      text: text.slice(range.start, range.end),
      sentiment: range.sentiment,
      highlight: true,
    })

    cursor = range.end
  }

  if (cursor < text.length) {
    pieces.push({ text: text.slice(cursor), highlight: false })
  }

  return pieces
}

function ScoreRing({ score }: { score: number }) {
  const radius = 46
  const circumference = 2 * Math.PI * radius
  const filled = circumference * Math.min(1, Math.max(0, score))

  return (
    <div style={{ textAlign: 'center' }}>
      <svg className="score-ring" width="116" height="116" viewBox="0 0 116 116">
        <circle
          cx="58"
          cy="58"
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.07)"
          strokeWidth="5"
        />
        <motion.circle
          cx="58"
          cy="58"
          r={radius}
          fill="none"
          stroke="var(--warn)"
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - filled }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          transform="rotate(-90 58 58)"
        />
        <text
          x="58"
          y="56"
          textAnchor="middle"
          fill="#fff"
          fontFamily="var(--font-mono)"
          fontSize="22"
        >
          {Math.round(score * 100)}
        </text>
        <text
          x="58"
          y="74"
          textAnchor="middle"
          fill="#8A94A6"
          fontFamily="var(--font-sans, Inter)"
          fontSize="9"
          letterSpacing="1.4"
        >
          DIVERGENCE
        </text>
      </svg>
      <div className="score-caption">score</div>
    </div>
  )
}

export function DivergenceView({
  divergence,
  loading,
}: {
  divergence: Divergence | null
  loading: boolean
}) {
  const pieces = useMemo(
    () =>
      (divergence?.variants ?? []).map(variant => ({
        variant,
        pieces: splitHighlights(variant.text, variant.highlights ?? []),
      })),
    [divergence],
  )

  if (loading || !divergence) {
    return (
      <section>
        <div className="view-head">
          <div>
            <h2 className="view-title">Language divergence</h2>
            <p className="view-desc">Same event, three languages, one disagreement score.</p>
          </div>
        </div>
        <div className="card divergence-banner">
          <SkeletonBlock height={116} width={116} radius={58} />
          <div style={{ flex: 1 }}>
            <SkeletonBlock height={22} width="60%" />
            <div style={{ height: 10 }} />
            <SkeletonBlock height={12} width="90%" />
            <div style={{ height: 7 }} />
            <SkeletonBlock height={12} width="76%" />
          </div>
        </div>
      </section>
    )
  }

  const variantCount = divergence.variants.length
  const disagreeing = divergence.variants.filter(
    variant => variant.sentiment !== divergence.variants[0]?.sentiment,
  ).length

  return (
    <section>
      <div className="view-head">
        <div>
          <h2 className="view-title">Language divergence</h2>
          <p className="view-desc">
            The same event, read in English, Hindi and Telugu. Where the languages disagree on
            sentiment, the phrases that carry the difference are highlighted.
          </p>
        </div>

        <div className="view-meta">
          {disagreeing} of {variantCount} differ
        </div>
      </div>

      <div className="card divergence-banner">
        <ScoreRing score={divergence.score} />

        <div className="divergence-copy">
          <h3 className="divergence-title">{divergence.title}</h3>
          <p className="divergence-summary">{divergence.summary}</p>
          <div className="divergence-note">
            <AlertTriangle size={14} strokeWidth={1.9} style={{ flexShrink: 0, marginTop: 1 }} />
            {divergence.note}
          </div>
        </div>
      </div>

      <div className="lang-grid">
        {pieces.map(({ variant, pieces: parts }) => (
          <article className="card lang-card" key={variant.language}>
            <header className="lang-head">
              <span className="lang-name">
                <span className="flag" aria-hidden="true">
                  {languageFlag(variant.language)}
                </span>
                {variant.label}
              </span>
              <SentimentChip sentiment={variant.sentiment} />
            </header>

            <p className="lang-text">
              {parts.map((piece, index) =>
                piece.highlight ? (
                  <mark
                    key={`${variant.language}-${index}`}
                    className={`hl-${sentimentTone(piece.sentiment ?? variant.sentiment)}`}
                    title={`${piece.sentiment ?? variant.sentiment} signal`}
                  >
                    {piece.text}
                  </mark>
                ) : (
                  <span key={`${variant.language}-${index}`}>{piece.text}</span>
                ),
              )}
            </p>

            <footer className="lang-foot">
              <span>{variant.source}</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
                <span className="conf-track">
                  <motion.span
                    initial={{ width: 0 }}
                    animate={{ width: percent(variant.confidence) }}
                    transition={{ duration: 0.7, ease: 'easeOut' }}
                    style={{
                      background: `var(--${sentimentTone(variant.sentiment) === 'bullish' ? 'pos' : sentimentTone(variant.sentiment) === 'bearish' ? 'neg' : 'muted'})`,
                    }}
                  />
                </span>
                {percent(variant.confidence)}
              </span>
            </footer>
          </article>
        ))}
      </div>

      <div className="divergence-foot">
        <span>
          Agreement {percent(divergence.agreement)} · disagreement {percent(divergence.score)}
        </span>
        <span>Highlights mark the phrases that drive the split.</span>
      </div>
    </section>
  )
}
