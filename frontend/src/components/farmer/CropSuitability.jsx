import { useEffect, useRef, useState } from 'react'
import { fetchSuitability } from '../../api'

const GRADE_STYLES = {
  highly_suitable: {
    bar:    'bg-forest-700',
    badge:  'bg-forest-100 text-forest-800',
    border: 'border-forest-200',
    ring:   'ring-forest-500',
    label:  'Highly Suitable',
  },
  suitable: {
    bar:    'bg-amber-500',
    badge:  'bg-amber-100 text-amber-800',
    border: 'border-amber-200',
    ring:   'ring-amber-400',
    label:  'Suitable',
  },
  marginal: {
    bar:    'bg-terra-500',
    badge:  'bg-terra-100 text-terra-700',
    border: 'border-terra-200',
    ring:   'ring-terra-400',
    label:  'Marginal',
  },
  unsuitable: {
    bar:    'bg-crimson-600',
    badge:  'bg-crimson-100 text-crimson-700',
    border: 'border-crimson-200',
    ring:   'ring-crimson-400',
    label:  'Not Suitable',
  },
}

function ScoreBar({ score, grade }) {
  const g = GRADE_STYLES[grade] ?? GRADE_STYLES.marginal
  return (
    <div className="relative w-full h-1.5 bg-earth-100 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-700 ${g.bar}`}
        style={{ width: `${score}%` }}
      />
    </div>
  )
}

function CropCard({ crop, isTop, lang }) {
  const g = GRADE_STYLES[crop.grade] ?? GRADE_STYLES.marginal
  const name = lang === 'te' ? crop.display_te : crop.display

  return (
    <div className={`relative bg-white rounded-xl border p-4 flex flex-col gap-2.5 transition-all duration-200
      ${isTop ? `${g.border} ring-1 ${g.ring} shadow-card` : 'border-earth-100 shadow-sm'}`}
    >
      {isTop && (
        <div className="absolute -top-2 left-3">
          <span className="bg-forest-900 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">
            Best Match
          </span>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">{crop.emoji}</span>
          <div>
            <p className="text-sm font-semibold text-earth-900 leading-tight">{name}</p>
            {lang === 'en' && (
              <p className="text-[10px] text-earth-400 leading-none">{crop.display_te}</p>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className="font-display text-2xl font-semibold text-earth-900 leading-none">{crop.score}</p>
          <p className="text-[9px] text-earth-400">/100</p>
        </div>
      </div>

      <ScoreBar score={crop.score} grade={crop.grade} />

      <span className={`self-start text-[10px] font-semibold px-2 py-0.5 rounded-full ${g.badge}`}>
        {crop.grade_label}
      </span>

      {/* Constraints */}
      {crop.constraints?.length > 0 && (
        <div className="flex flex-col gap-1">
          {crop.constraints.map((c, i) => (
            <div key={i} className="flex items-start gap-1.5 text-[10px] text-earth-600">
              <svg className="w-3 h-3 mt-0.5 shrink-0 text-terra-500" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
              </svg>
              <span>{c}</span>
            </div>
          ))}
        </div>
      )}

      {/* Strengths (only on top card to keep it clean) */}
      {isTop && crop.strengths?.length > 0 && (
        <div className="flex flex-col gap-1">
          {crop.strengths.map((s, i) => (
            <div key={i} className="flex items-center gap-1.5 text-[10px] text-forest-700">
              <svg className="w-3 h-3 shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
              </svg>
              <span>{s}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function CropSuitability({ soil, lang }) {
  const [result,  setResult]  = useState(null)
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef(null)

  useEffect(() => {
    // Debounce: wait 600ms after slider stops before calling API
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setLoading(true)
      fetchSuitability(soil)
        .then(r => { setResult(r); setLoading(false) })
        .catch(() => setLoading(false))
    }, 600)

    return () => clearTimeout(debounceRef.current)
  }, [JSON.stringify(soil)])  // re-run when any soil value changes

  return (
    <div className="card">
      <div className="card-header justify-between">
        <div>
          <h3 className="text-sm font-semibold text-earth-900">Crop Suitability</h3>
          <p className="text-[10px] text-earth-400 mt-0.5">Ranked by your current soil values</p>
        </div>
        {loading && (
          <div className="w-4 h-4 rounded-full border-2 border-forest-700 border-t-transparent animate-spin" />
        )}
      </div>

      <div className="p-4">
        {/* EC warning banner */}
        {result?.ec_warning && (
          <div className="flex items-start gap-2 bg-crimson-100 border border-crimson-200 rounded-xl px-3 py-2.5 mb-3">
            <svg className="w-4 h-4 mt-0.5 shrink-0 text-crimson-600" viewBox="0 0 24 24" fill="currentColor">
              <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/>
            </svg>
            <p className="text-xs text-crimson-800">{result.ec_warning}</p>
          </div>
        )}

        {/* Summary line */}
        {result?.summary && !result.ec_warning && (
          <p className="text-xs text-earth-600 mb-3 leading-relaxed">{result.summary}</p>
        )}

        {/* Crop grid */}
        {result ? (
          <div className="grid grid-cols-2 gap-3">
            {result.rankings.map((crop, i) => (
              <CropCard
                key={crop.crop}
                crop={crop}
                isTop={i === 0}
                lang={lang}
              />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {[1,2,3,4].map(i => (
              <div key={i} className="h-28 bg-earth-50 rounded-xl animate-pulse" />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
