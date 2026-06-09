import { PARAM_LABELS, PARAM_UNITS } from '../../api'

function statusColor(avgConf, defPct) {
  if (defPct > 60 || avgConf < 0.5) return { bar: '#9B2335', conf: 'text-crimson-600 bg-crimson-100', def: 'text-crimson-700 bg-crimson-100' }
  if (defPct > 30 || avgConf < 0.75) return { bar: '#C4622D', conf: 'text-terra-600 bg-terra-100', def: 'text-terra-600 bg-terra-100' }
  return { bar: '#1B4332', conf: 'text-forest-700 bg-forest-100', def: 'text-forest-700 bg-forest-100' }
}

function KPICard({ param, stats }) {
  const unit = PARAM_UNITS[param]
  const sc   = statusColor(stats.avg_confidence, stats.deficiency_pct)

  return (
    <div
      className="bg-white rounded-2xl border border-earth-100 shadow-card p-4 relative overflow-hidden flex flex-col gap-3 hover:shadow-card-lg transition-shadow duration-200"
    >
      {/* Colored status bar on top */}
      <div className="absolute inset-x-0 top-0 h-[3px] rounded-t-2xl" style={{ background: sc.bar }} />

      <p className="section-title pt-1 truncate">{PARAM_LABELS[param]}</p>

      {/* Big serif number */}
      <div className="flex items-baseline gap-1">
        <span className="font-display text-[2.4rem] font-semibold leading-none text-earth-950">
          {stats.mean.toFixed(2)}
        </span>
        {unit && (
          <span className="text-xs text-earth-500 font-sans mb-0.5">{unit}</span>
        )}
      </div>

      {/* Badges row */}
      <div className="flex flex-wrap gap-1.5">
        <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full ${sc.conf}`}>
          <svg className="w-2.5 h-2.5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/>
          </svg>
          {(stats.avg_confidence * 100).toFixed(0)}% conf
        </span>
        <span className={`inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded-full ${sc.def}`}>
          {stats.deficiency_pct.toFixed(0)}% low
        </span>
      </div>
    </div>
  )
}

function Skeleton() {
  return (
    <div className="bg-white rounded-2xl border border-earth-100 shadow-card p-4 animate-pulse">
      <div className="h-2.5 w-16 bg-earth-100 rounded mb-4" />
      <div className="h-10 w-24 bg-earth-100 rounded mb-3" />
      <div className="flex gap-1.5">
        <div className="h-5 w-16 bg-earth-100 rounded-full" />
        <div className="h-5 w-12 bg-earth-100 rounded-full" />
      </div>
    </div>
  )
}

export default function KPICards({ stats, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
        {Array.from({ length: 10 }).map((_, i) => <Skeleton key={i} />)}
      </div>
    )
  }

  if (!stats || Object.keys(stats).length === 0) {
    return (
      <div className="mb-6 flex items-start gap-3 bg-forest-50 border border-forest-200 rounded-2xl px-5 py-4 text-sm text-forest-800">
        <svg className="w-4 h-4 mt-0.5 shrink-0 text-forest-600" viewBox="0 0 24 24" fill="currentColor">
          <path d="M11 7h2v2h-2zm0 4h2v6h-2zm1-9C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
        </svg>
        <span>
          No prediction maps found. Run{' '}
          <code className="font-mono bg-forest-100 px-1.5 py-0.5 rounded text-xs">
            python pipeline/05_predict_maps.py --all-params
          </code>{' '}
          to populate this panel.
        </span>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
      {Object.entries(stats).map(([param, s]) => (
        <KPICard key={param} param={param} stats={s} />
      ))}
    </div>
  )
}
