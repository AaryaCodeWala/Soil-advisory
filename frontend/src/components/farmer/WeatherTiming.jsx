import { useEffect, useState } from 'react'
import { fetchWeatherTiming } from '../../api'

const RISK = {
  low:    { bg: 'bg-forest-100',  bar: 'bg-forest-600',  text: 'text-forest-700',  dot: 'bg-forest-500',  label: 'Safe'    },
  medium: { bg: 'bg-amber-100',   bar: 'bg-amber-500',   text: 'text-amber-700',   dot: 'bg-amber-500',   label: 'Caution' },
  high:   { bg: 'bg-crimson-100', bar: 'bg-crimson-600', text: 'text-crimson-700', dot: 'bg-crimson-500', label: 'Avoid'   },
}

const ADVICE_ICONS = {
  low:    { icon: '✓', bg: 'bg-forest-50 border-forest-200', text: 'text-forest-800' },
  medium: { icon: '⚠', bg: 'bg-amber-50 border-amber-200',   text: 'text-amber-900'  },
  high:   { icon: '✗', bg: 'bg-crimson-50 border-crimson-200', text: 'text-crimson-900' },
}

function DayColumn({ day }) {
  const r  = RISK[day.risk] ?? RISK.medium
  const pct = Math.min(100, day.rain_prob)

  return (
    <div className={`flex flex-col items-center gap-1.5 px-2 py-2.5 rounded-xl ${day.apply ? '' : 'opacity-80'}`}>
      {/* Day label */}
      <p className="text-[10px] font-semibold text-earth-500 uppercase tracking-wider whitespace-nowrap">
        {day.day_label}
      </p>

      {/* Rain probability bar */}
      <div className="relative w-5 flex flex-col-reverse" style={{ height: 56 }}>
        <div className="absolute inset-0 bg-earth-100 rounded-full" />
        <div
          className={`absolute bottom-0 left-0 right-0 rounded-full ${r.bar} transition-all duration-500`}
          style={{ height: `${pct}%` }}
        />
      </div>

      {/* Probability % */}
      <p className={`text-[10px] font-bold tabular-nums ${r.text}`}>{day.rain_prob}%</p>

      {/* mm */}
      <p className="text-[9px] text-earth-400 tabular-nums">{day.rain_mm}mm</p>

      {/* Risk dot */}
      <div className={`w-2 h-2 rounded-full ${r.dot}`} title={r.label} />

      {/* Apply indicator */}
      {day.apply && (
        <svg className="w-3.5 h-3.5 text-forest-600" viewBox="0 0 24 24" fill="currentColor">
          <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
        </svg>
      )}
    </div>
  )
}

export default function WeatherTiming() {
  const [weather, setWeather] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    fetchWeatherTiming()
      .then(d => { setWeather(d); setLoading(false) })
      .catch(() => { setError('Weather unavailable'); setLoading(false) })
  }, [])

  if (loading) {
    return (
      <div className="card p-4 flex items-center gap-3 text-xs text-earth-500">
        <div className="w-4 h-4 rounded-full border-2 border-forest-700 border-t-transparent animate-spin shrink-0" />
        Fetching 7-day rain forecast for Krishna District…
      </div>
    )
  }

  if (error || !weather) {
    return (
      <div className="card p-4 text-xs text-earth-400 flex items-center gap-2">
        <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="currentColor">
          <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z"/>
        </svg>
        Weather data unavailable — check internet connection.
      </div>
    )
  }

  const advice = ADVICE_ICONS[weather.today_risk] ?? ADVICE_ICONS.medium
  const safeDays = weather.days.filter(d => d.apply)

  return (
    <div className="card">
      <div className="card-header justify-between">
        <div>
          <h3 className="text-sm font-semibold text-earth-900">Application Timing</h3>
          <p className="text-[10px] text-earth-400 mt-0.5">{weather.location} · {weather.fetched_at}</p>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-earth-500">
          <div className="flex gap-1 items-center">
            <span className="w-2 h-2 rounded-full bg-forest-500 inline-block" /> Safe
          </div>
          <div className="flex gap-1 items-center">
            <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" /> Caution
          </div>
          <div className="flex gap-1 items-center">
            <span className="w-2 h-2 rounded-full bg-crimson-500 inline-block" /> Avoid
          </div>
        </div>
      </div>

      <div className="p-4 flex flex-col gap-3">
        {/* Advice banner */}
        <div className={`flex items-start gap-2.5 border rounded-xl px-3.5 py-3 ${advice.bg}`}>
          <span className={`text-base font-bold ${advice.text} shrink-0 leading-none mt-0.5`}>
            {advice.icon}
          </span>
          <p className={`text-xs font-medium leading-relaxed ${advice.text}`}>{weather.advice}</p>
        </div>

        {/* 7-day bar chart */}
        <div className="flex justify-between items-end px-1">
          {weather.days.map((day, i) => (
            <DayColumn key={i} day={day} />
          ))}
        </div>

        {/* Safe windows summary */}
        {safeDays.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] text-earth-500 uppercase tracking-wider font-semibold">Safe windows:</span>
            {safeDays.map((d, i) => (
              <span key={i} className="text-[10px] bg-forest-100 text-forest-700 font-semibold px-2 py-0.5 rounded-full">
                {d.day_label}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
