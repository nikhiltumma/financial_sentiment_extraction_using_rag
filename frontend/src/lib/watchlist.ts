import { useCallback, useEffect, useState } from 'react'

const KEY = 'signalradar.watchlist'

function read(): string[] {
  try {
    const raw = window.localStorage.getItem(KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : []

    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : []
  } catch {
    return []
  }
}

export function useWatchlist(): {
  ids: string[]
  has: (id: string) => boolean
  toggle: (id: string) => boolean
} {
  const [ids, setIds] = useState<string[]>(() => read())

  useEffect(() => {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(ids))
    } catch {
      // Storage can be unavailable in private mode; the list stays in memory.
    }
  }, [ids])

  const has = useCallback((id: string) => ids.includes(id), [ids])

  const toggle = useCallback((id: string) => {
    let added = false

    setIds(current => {
      added = !current.includes(id)
      return added ? [...current, id] : current.filter(item => item !== id)
    })

    return added
  }, [])

  return { ids, has, toggle }
}
