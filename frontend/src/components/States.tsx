import { Radar } from 'lucide-react'
import type { ReactNode } from 'react'

export function EventSkeleton() {
  return (
    <div className="card event-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div className="skeleton" style={{ height: 16, width: '58%' }} />
        <div className="skeleton" style={{ height: 18, width: 74, borderRadius: 999 }} />
      </div>
      <div className="skeleton" style={{ height: 11, width: '92%', marginTop: 12 }} />
      <div className="skeleton" style={{ height: 11, width: '74%', marginTop: 7 }} />
      <div style={{ display: 'flex', gap: 6, marginTop: 14 }}>
        <div className="skeleton" style={{ height: 18, width: 92 }} />
        <div className="skeleton" style={{ height: 18, width: 68 }} />
      </div>
    </div>
  )
}

export function SkeletonBlock({
  height,
  width = '100%',
  radius,
}: {
  height: number
  width?: number | string
  radius?: number
}) {
  return (
    <div
      className="skeleton"
      style={{ height, width, borderRadius: radius ?? 8 }}
      aria-hidden="true"
    />
  )
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Radar size={19} strokeWidth={1.6} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  )
}
