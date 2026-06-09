import { useState, useEffect } from 'react'
import { fetchAllStats, SOIL_PARAMS, PARAM_LABELS, PARAM_UNITS } from '../../api'
import KPICards from './KPICards'
import SoilMap from './SoilMap'
import { DeficiencyBar, ConfidenceGauge } from './Charts'

const LAYER_OPTIONS = [
  { value: 'value',      label: 'Predicted Value' },
  { value: 'confidence', label: 'Confidence Score' },
]

function StatsRow({ label, value }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-earth-50 last:border-0">
      <span className="text-xs text-earth-500">{label}</span>
      <span className="text-xs font-semibold text-earth-900 font-display">{value}</span>
    </div>
  )
}

export default function OfficialsDashboard() {
  const [stats,   setStats]   = useState({})
  const [loading, setLoading] = useState(true)
  const [param,   setParam]   = useState('pH')
  const [layer,   setLayer]   = useState('value')

  useEffect(() => {
    fetchAllStats().then(s => { setStats(s); setLoading(false) })
    const id = setInterval(() => fetchAllStats().then(setStats), 30_000)
    return () => clearInterval(id)
  }, [])

  const s    = stats[param]
  const unit = PARAM_UNITS[param]

  return (
    <div>
      <KPICards stats={stats} loading={loading} />

      {/* Map + controls */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5 mb-5">
        {/* ── Controls panel ── */}
        <div className="card flex flex-col gap-5 p-5">
          {/* Parameter selector */}
          <div>
            <label className="section-title block mb-2">Parameter</label>
            <select
              value={param}
              onChange={e => setParam(e.target.value)}
              className="field-input"
            >
              {SOIL_PARAMS.map(p => (
                <option key={p} value={p}>{PARAM_LABELS[p]}</option>
              ))}
            </select>
          </div>

          {/* Layer toggle */}
          <div>
            <label className="section-title block mb-2">Colour by</label>
            <div className="flex rounded-xl overflow-hidden border border-earth-200 text-xs font-semibold">
              {LAYER_OPTIONS.map(o => (
                <button
                  key={o.value}
                  onClick={() => setLayer(o.value)}
                  className={`flex-1 py-2.5 transition-colors text-center ${
                    layer === o.value
                      ? 'bg-forest-900 text-white'
                      : 'bg-white text-earth-600 hover:bg-earth-50'
                  }`}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          {/* Stats */}
          <div className="border-t border-earth-100 pt-4">
            <p className="section-title mb-3">{PARAM_LABELS[param]}</p>
            {s ? (
              <>
                <StatsRow label="Mean"       value={`${s.mean.toFixed(3)} ${unit}`} />
                <StatsRow label="Std dev"    value={s.std.toFixed(3)} />
                <StatsRow label="Median"     value={`${s.median.toFixed(3)} ${unit}`} />
                <StatsRow label="5th pct"    value={`${s.p5.toFixed(3)} ${unit}`} />
                <StatsRow label="95th pct"   value={`${s.p95.toFixed(3)} ${unit}`} />
                <StatsRow label="Avg conf"   value={`${(s.avg_confidence * 100).toFixed(1)}%`} />
                <StatsRow label="% deficient" value={`${s.deficiency_pct.toFixed(1)}%`} />
              </>
            ) : (
              <p className="text-xs text-earth-400 italic">No data</p>
            )}
          </div>
        </div>

        {/* ── Map ── */}
        <div className="lg:col-span-3 card overflow-hidden" style={{ height: 500 }}>
          <div className="card-header justify-between">
            <h2 className="text-sm font-semibold text-earth-900">
              Soil Parameter Map — Krishna District
            </h2>
            <span className="text-[10px] font-medium text-earth-400 uppercase tracking-wider">
              {layer === 'value' ? PARAM_LABELS[param] : 'Confidence'}
            </span>
          </div>
          <div style={{ height: 'calc(100% - 52px)' }}>
            <SoilMap param={param} layer={layer} />
          </div>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 card p-5">
          <h2 className="text-sm font-semibold text-earth-900 mb-1">
            District Deficiency Overview
          </h2>
          <p className="text-xs text-earth-500 mb-4">% of mapped area below ICAR low threshold</p>
          <DeficiencyBar stats={stats} />
        </div>

        <div className="card p-5 flex flex-col">
          <h2 className="text-sm font-semibold text-earth-900 mb-1">
            Prediction Confidence
          </h2>
          <p className="text-xs text-earth-500 mb-4">{PARAM_LABELS[param]}</p>
          <div className="flex-1 flex items-center justify-center">
            <ConfidenceGauge stats={stats} param={param} />
          </div>
        </div>
      </div>
    </div>
  )
}
