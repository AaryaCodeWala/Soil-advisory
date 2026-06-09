import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, CartesianGrid,
} from 'recharts'
import { PARAM_LABELS } from '../../api'

function barFill(pct) {
  if (pct > 60) return '#9B2335'
  if (pct > 30) return '#C4622D'
  return '#1B4332'
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-earth-200 rounded-xl shadow-card-lg px-3 py-2 text-xs">
      <p className="font-semibold text-earth-700 mb-0.5">{PARAM_LABELS[label] ?? label}</p>
      <p className="text-earth-950 font-display text-base">{payload[0].value.toFixed(1)}%</p>
      <p className="text-earth-400">area below threshold</p>
    </div>
  )
}

export function DeficiencyBar({ stats }) {
  if (!stats || Object.keys(stats).length === 0) {
    return (
      <div className="flex items-center justify-center h-52 text-earth-400 text-sm">
        No data yet
      </div>
    )
  }

  const data = Object.entries(stats).map(([param, s]) => ({
    name: param,
    pct:  Math.round(s.deficiency_pct * 10) / 10,
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#EDE8E0" />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: '#6B6560', fontFamily: 'DM Sans' }}
          axisLine={false} tickLine={false}
        />
        <YAxis
          domain={[0, 100]} tick={{ fontSize: 10, fill: '#A89E97', fontFamily: 'DM Sans' }}
          axisLine={false} tickLine={false} unit="%"
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(27,67,50,0.04)', radius: 6 }} />
        <Bar dataKey="pct" radius={[5, 5, 0, 0]} maxBarSize={36}>
          {data.map((d, i) => (
            <Cell key={i} fill={barFill(d.pct)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// SVG arc gauge — much more impressive than a histogram
export function ConfidenceGauge({ stats, param }) {
  const s = stats?.[param]
  if (!s) {
    return (
      <div className="flex items-center justify-center h-52 text-earth-400 text-sm">
        No data yet
      </div>
    )
  }

  const conf    = s.avg_confidence
  const highPct = s.high_confidence_pct ?? 0

  // Arc geometry
  const r    = 58
  const cx   = 80
  const cy   = 78
  const circ = Math.PI * r   // half-circle circumference
  const offset = circ * (1 - conf)

  // Color by confidence level
  const arcColor = conf >= 0.75 ? '#1B4332' : conf >= 0.5 ? '#C4622D' : '#9B2335'
  const arcLight = conf >= 0.75 ? '#D8F3DC' : conf >= 0.5 ? '#FEF0E8' : '#FDE8EC'

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width="160" height="100" viewBox="0 0 160 100" className="overflow-visible">
        {/* Track */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none" stroke={arcLight} strokeWidth="12" strokeLinecap="round"
        />
        {/* Value */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none" stroke={arcColor} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
        {/* Center number */}
        <text
          x={cx} y={cy - 12} textAnchor="middle"
          style={{ fontFamily: 'Cormorant Garamond', fontSize: '28px', fontWeight: '600', fill: arcColor }}
        >
          {(conf * 100).toFixed(0)}%
        </text>
        <text
          x={cx} y={cy + 6} textAnchor="middle"
          style={{ fontFamily: 'DM Sans', fontSize: '9px', fill: '#A89E97', letterSpacing: '0.08em', textTransform: 'uppercase' }}
        >
          avg confidence
        </text>
      </svg>

      {/* Stats below gauge */}
      <div className="flex gap-6 text-center">
        <div>
          <p className="font-display text-xl font-semibold text-earth-950">{highPct.toFixed(1)}%</p>
          <p className="text-[10px] text-earth-500 uppercase tracking-wide">High-conf area</p>
        </div>
        <div className="w-px bg-earth-200" />
        <div>
          <p className="font-display text-xl font-semibold text-earth-950">{s.count_valid_pixels?.toLocaleString() ?? '—'}</p>
          <p className="text-[10px] text-earth-500 uppercase tracking-wide">Valid pixels</p>
        </div>
      </div>
    </div>
  )
}
