import { useEffect, useRef, useState } from 'react'

export function CountUp({
  value,
  duration = 700,
  decimals = 0,
}: {
  value: number
  duration?: number
  decimals?: number
}) {
  const [display, setDisplay] = useState(0)
  const frame = useRef<number>(0)
  const started = useRef(false)

  useEffect(() => {
    if (started.current) {
      setDisplay(value)
      return
    }

    started.current = true

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reduced) {
      setDisplay(value)
      return
    }

    const start = performance.now()
    const from = 0

    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(from + (value - from) * eased)

      if (progress < 1) {
        frame.current = requestAnimationFrame(tick)
      }
    }

    frame.current = requestAnimationFrame(tick)

    return () => cancelAnimationFrame(frame.current)
  }, [value, duration])

  useEffect(() => {
    setDisplay(current => (Math.abs(current - value) < 0.01 ? value : current))
  }, [value])

  return <>{display.toFixed(decimals)}</>
}
