import { motion } from 'framer-motion'
import { impactLabel } from '../lib/format.ts'
import type { Sentiment } from '../lib/types.ts'
import { sentimentTone } from '../lib/format.ts'

const TONE_COLOR: Record<string, string> = {
  bullish: 'var(--pos)',
  bearish: 'var(--neg)',
  neutral: 'var(--muted)',
}

export function ImpactMeter({
  value,
  sentiment,
}: {
  value: number
  sentiment: Sentiment
}) {
  const color = TONE_COLOR[sentimentTone(sentiment)] ?? 'var(--muted)'

  return (
    <div className="impact" title={`Impact ${value}/100 · ${impactLabel(value)}`}>
      <span className="impact-label">{impactLabel(value)}</span>
      <div className="impact-track">
        <motion.div
          className="impact-fill"
          style={{ background: `linear-gradient(90deg, ${color}, ${color}99)` }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(4, value)}%` }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
      <span className="impact-value mono">{value}</span>
    </div>
  )
}
