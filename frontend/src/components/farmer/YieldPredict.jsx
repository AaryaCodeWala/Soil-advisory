import { useState, useMemo } from 'react'

const BASE_YIELD     = { paddy: 4.0, cotton: 1.4, groundnut: 1.8, red_gram: 0.9 }
const MAX_YIELD      = { paddy: 7.0, cotton: 2.8, groundnut: 3.2, red_gram: 2.0 }
const DISTRICT_AVG   = { paddy: 4.8, cotton: 1.9, groundnut: 2.3, red_gram: 1.2 }
const MSP            = { paddy: 2183, cotton: 6620, groundnut: 6377, red_gram: 7000 }

const CROPS = {
  paddy:     'Paddy (వరి)',
  cotton:    'Cotton (పత్తి)',
  groundnut: 'Groundnut (వేరుసెనగ)',
  red_gram:  'Red Gram (కందులు)',
}

const N_ADEQUATE = { paddy: 280, cotton: 320, groundnut: 100, red_gram: 80 }
const P_ADEQUATE = { paddy: 22,  cotton: 28,  groundnut: 20,  red_gram: 16 }

function soilYieldFactor(soil, crop) {
  let f = 1.0
  if (soil.pH < 5.5 || soil.pH > 8.5)       f *= 0.6
  else if (soil.pH < 6.0 || soil.pH > 8.0)  f *= 0.8
  else if (soil.pH < 6.5 || soil.pH > 7.5)  f *= 0.92

  f *= Math.min(1, 0.5 + 0.5 * (soil.N / N_ADEQUATE[crop]))
  f *= Math.min(1, 0.6 + 0.4 * (soil.P / P_ADEQUATE[crop]))

  if (soil.OC < 0.3)      f *= 0.85
  else if (soil.OC < 0.5) f *= 0.93

  if (soil.Zn < 0.5) f *= 0.92

  return Math.min(f, 1.0)
}

const SLIDERS = [
  { id: 'pH', label: 'pH',       unit: '',        min: 4,   max: 10,  step: 0.1  },
  { id: 'OC', label: 'OC',       unit: '%',       min: 0,   max: 2.5, step: 0.05 },
  { id: 'N',  label: 'N',        unit: 'kg/ha',   min: 0,   max: 600, step: 10   },
  { id: 'P',  label: 'P',        unit: 'kg/ha',   min: 0,   max: 80,  step: 1    },
  { id: 'Zn', label: 'Zinc',     unit: 'ppm',     min: 0,   max: 2,   step: 0.1  },
]

function YieldBar({ label, value, maxValue, color, subtext }) {
  const pct = maxValue > 0 ? Math.min(100, (value / maxValue) * 100) : 0
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-earth-600 w-36 shrink-0">{label}</span>
      <div className="flex-1 h-6 bg-earth-100 rounded-lg overflow-hidden relative">
        <div
          className={`h-full rounded-lg ${color} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="text-right w-20 shrink-0">
        <span className="font-display text-sm font-semibold text-earth-900 tabular-nums">{value.toFixed(2)}</span>
        <span className="text-[10px] text-earth-400 ml-1">t/ha</span>
      </div>
    </div>
  )
}

export default function YieldPredict() {
  const [crop, setCrop] = useState('paddy')
  const [area, setArea] = useState(2)
  const [soil, setSoil] = useState({ pH: 6.8, OC: 0.45, N: 200, P: 18, K: 150, Zn: 0.4 })

  const currentYield = useMemo(() => {
    const factor = soilYieldFactor(soil, crop)
    return BASE_YIELD[crop] + factor * (MAX_YIELD[crop] - BASE_YIELD[crop])
  }, [soil, crop])

  const optimizedYield = useMemo(() => {
    return BASE_YIELD[crop] + 0.92 * (MAX_YIELD[crop] - BASE_YIELD[crop])
  }, [crop])

  const districtAvg = DISTRICT_AVG[crop]
  const maxBar = MAX_YIELD[crop]

  const currentColor = currentYield >= districtAvg ? 'bg-forest-600' : 'bg-amber-500'

  const areaHa = area * 0.405
  const yieldGapTons = (optimizedYield - currentYield) * areaHa
  const revenueGain = yieldGapTons * 10 * MSP[crop]

  return (
    <div className="flex flex-col gap-6">
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="text-sm font-semibold text-earth-900">Yield Prediction</h2>
            <p className="text-[10px] text-earth-400 mt-0.5">దిగుబడి అంచనా · Based on soil nutrient levels</p>
          </div>
        </div>

        <div className="p-5 flex flex-col gap-6">
          <div className="flex flex-col gap-4">
            <div>
              <p className="section-title mb-2">Crop</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(CROPS).map(([k, v]) => (
                  <button
                    key={k}
                    onClick={() => setCrop(k)}
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                      crop === k
                        ? 'bg-forest-900 text-white shadow-sm'
                        : 'bg-earth-100 text-earth-600 hover:bg-earth-200'
                    }`}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>

            <div className="w-32">
              <label className="section-title block mb-1.5">Area (acres)</label>
              <input
                type="number"
                min={0.5}
                step={0.5}
                value={area}
                onChange={e => setArea(Math.max(0.5, parseFloat(e.target.value) || 0.5))}
                className="field-input"
              />
            </div>
          </div>

          <div>
            <p className="section-title mb-4">Soil Parameters</p>
            <div className="flex flex-col gap-5">
              {SLIDERS.map(s => {
                const pct = ((soil[s.id] - s.min) / (s.max - s.min)) * 100
                return (
                  <div key={s.id}>
                    <div className="flex justify-between items-center mb-1.5">
                      <label className="text-xs font-semibold text-earth-700">
                        {s.label}
                        {s.unit && <span className="text-earth-400 font-normal ml-1">({s.unit})</span>}
                      </label>
                      <span className="font-display text-sm font-semibold text-forest-900 tabular-nums">{soil[s.id]}</span>
                    </div>
                    <div className="relative h-2 bg-earth-100 rounded-full">
                      <div
                        className="absolute left-0 top-0 h-full bg-forest-600 rounded-full pointer-events-none transition-all duration-200"
                        style={{ width: `${pct}%` }}
                      />
                      <input
                        type="range"
                        min={s.min}
                        max={s.max}
                        step={s.step}
                        value={soil[s.id]}
                        onChange={e => setSoil(p => ({ ...p, [s.id]: parseFloat(e.target.value) }))}
                        className="absolute inset-0 w-full opacity-0 cursor-pointer h-full"
                      />
                    </div>
                    <div className="flex justify-between mt-1">
                      <span className="text-[9px] text-earth-400">{s.min}</span>
                      <span className="text-[9px] text-earth-400">{s.max}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <div>
            <p className="section-title mb-3">Yield Comparison</p>
            <div className="flex flex-col gap-3">
              <YieldBar
                label="Current (your soil)"
                value={currentYield}
                maxValue={maxBar}
                color={currentColor}
              />
              <YieldBar
                label="With Optimized Fertilizer"
                value={optimizedYield}
                maxValue={maxBar}
                color="bg-forest-800"
              />
              <YieldBar
                label="District Average"
                value={districtAvg}
                maxValue={maxBar}
                color="bg-earth-400"
              />
            </div>
          </div>

          <div className="bg-forest-100 border border-forest-300 rounded-2xl p-4">
            <p className="section-title text-forest-700 mb-1">Yield Gap Opportunity</p>
            <p className="text-sm text-forest-900 mt-1 leading-relaxed">
              Closing the yield gap from{' '}
              <span className="font-semibold">{currentYield.toFixed(2)} t/ha</span>
              {' '}to{' '}
              <span className="font-semibold">{optimizedYield.toFixed(2)} t/ha</span>
              {' '}over{' '}
              <span className="font-semibold">{area} acres</span>
              {' '}adds{' '}
              <span className="font-display text-base font-semibold text-forest-800">
                ₹{Math.round(revenueGain).toLocaleString('en-IN')}
              </span>
              {' '}in revenue.
            </p>
          </div>

          <p className="text-[10px] text-earth-400 leading-relaxed">
            Estimates based on ICAR AP response curves. Actual yield varies by weather and variety.
          </p>
        </div>
      </div>
    </div>
  )
}
