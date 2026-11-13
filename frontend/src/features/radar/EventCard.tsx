import { motion } from 'framer-motion'
import { Star } from 'lucide-react'
import { SentimentChip } from '../../components/SentimentChip.tsx'
import { ImpactMeter } from '../../components/ImpactMeter.tsx'
import { useToast } from '../../components/Toast.tsx'
import { languageFlag, languageLabel, relativeTime } from '../../lib/format.ts'
import type { EventItem } from '../../lib/types.ts'

export function EventCard({
  event,
  watched,
  onToggleWatch,
}: {
  event: EventItem
  watched: boolean
  onToggleWatch: (id: string) => void
}) {
  const toast = useToast()

  return (
    <motion.article className="card lift event-card" variants={{
      hidden: { opacity: 0, y: 10 },
      show: { opacity: 1, y: 0 },
    }}>
      <div className="event-top">
        <h3 className="event-title">{event.title}</h3>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
          <SentimentChip sentiment={event.sentiment} />
          <button
            type="button"
            className={`icon-btn${watched ? ' is-on' : ''}`}
            aria-label={watched ? 'Remove from watchlist' : 'Add to watchlist'}
            aria-pressed={watched}
            onClick={() => {
              onToggleWatch(event.id)
              toast(watched ? 'Removed from watchlist' : 'Added to watchlist')
            }}
          >
            <Star size={13} strokeWidth={1.9} fill={watched ? 'currentColor' : 'none'} />
          </button>
        </div>
      </div>

      <p className="event-summary">{event.summary}</p>

      <div className="event-entities">
        {event.entities.slice(0, 4).map(entity => (
          <span className="tag" key={entity}>
            {entity}
          </span>
        ))}
      </div>

      <div className="event-foot">
        <span className="event-source" title={event.source}>
          {event.source}
        </span>
        <i className="dot" />
        <span>{relativeTime(event.timestamp)}</span>
        <i className="dot" />
        <span title={languageLabel(event.language)}>
          {languageFlag(event.language)} {languageLabel(event.language)}
        </span>

        <ImpactMeter value={event.impact} sentiment={event.sentiment} />
      </div>
    </motion.article>
  )
}
