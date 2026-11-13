import type { Sentiment } from './types.ts'

export function sentimentTone(sentiment: Sentiment | string): 'bullish' | 'bearish' | 'neutral' {
  switch (String(sentiment).toLowerCase()) {
    case 'bullish':
      return 'bullish'
    case 'bearish':
      return 'bearish'
    default:
      return 'neutral'
  }
}

export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime()

  if (Number.isNaN(then)) {
    return 'unknown'
  }

  const minutes = Math.round((Date.now() - then) / 60000)

  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.round(minutes / 60)

  if (hours < 24) return `${hours}h ago`

  const days = Math.round(hours / 24)

  if (days === 1) return 'yesterday'
  if (days < 14) return `${days}d ago`

  return new Date(then).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
  })
}

export function languageLabel(code: string): string {
  switch (code) {
    case 'en':
      return 'English'
    case 'hi':
      return 'Hindi'
    case 'te':
      return 'Telugu'
    default:
      return code.toUpperCase()
  }
}

export function languageFlag(code: string): string {
  switch (code) {
    case 'en':
      return '🇬🇧'
    case 'hi':
      return '🇮🇳'
    case 'te':
      return '🇮🇳'
    default:
      return '🌐'
  }
}

export function percent(value: number): string {
  return `${Math.round(value * 100)}%`
}

export function impactLabel(value: number): string {
  if (value >= 85) return 'Critical'
  if (value >= 70) return 'High'
  if (value >= 50) return 'Moderate'
  return 'Low'
}

export function initials(label: string): string {
  return label
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(word => word[0]?.toUpperCase() ?? '')
    .join('')
}
