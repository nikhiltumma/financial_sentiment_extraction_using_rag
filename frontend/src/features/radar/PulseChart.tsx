import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { TimelinePoint } from '../../lib/types.ts'

function PulseTooltip({ active, payload }: { active?: boolean; payload?: { payload?: TimelinePoint }[] }) {
  const point = payload?.[0]?.payload

  if (!active || !point) {
    return null
  }

  return (
    <div className="chart-tooltip">
      <div className="muted">{point.label}</div>
      <strong>{point.score?.toFixed(1) ?? '—'}</strong>
      <div className="dim">
        {point.count === 0
          ? 'no filings · interpolated'
          : `${point.count} filing${point.count === 1 ? '' : 's'}`}
      </div>
    </div>
  )
}

export function PulseChart({ timeline }: { timeline: TimelinePoint[] }) {
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={timeline} margin={{ top: 8, right: 6, bottom: 0, left: 6 }}>
          <defs>
            <linearGradient id="pulseFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#5EEAD4" stopOpacity={0.28} />
              <stop offset="100%" stopColor="#5EEAD4" stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            interval={3}
            tick={{ fill: '#5F6A7B', fontSize: 9.5 }}
            dy={4}
          />
          <YAxis domain={[0, 100]} hide />
          <ReferenceLine y={50} stroke="rgba(255,255,255,0.12)" strokeDasharray="3 4" />

          <Tooltip
            content={<PulseTooltip />}
            cursor={{ stroke: 'rgba(94,234,212,0.35)', strokeWidth: 1 }}
          />

          <Area
            type="monotone"
            dataKey="score"
            stroke="#5EEAD4"
            strokeWidth={1.8}
            fill="url(#pulseFill)"
            dot={false}
            activeDot={{ r: 3, fill: '#5EEAD4', stroke: '#07090D', strokeWidth: 2 }}
            animationDuration={700}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
