import type { Sentiment } from '../lib/types.ts'
import { sentimentTone } from '../lib/format.ts'

export function SentimentChip({ sentiment }: { sentiment: Sentiment }) {
  return (
    <span className={`sentiment-chip sentiment-${sentimentTone(sentiment)}`}>{sentiment}</span>
  )
}
