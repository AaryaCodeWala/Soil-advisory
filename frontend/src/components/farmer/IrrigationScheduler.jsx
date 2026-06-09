import { useState, useEffect } from 'react'
import { fetchWeatherTiming } from '../../api'

const CROP_KC = {
  paddy:     { sowing: 1.05, vegetative: 1.2,  flowering: 1.25, harvest: 1.0  },
  cotton:    { sowing: 0.35, vegetative: 0.75, flowering: 1.1,  harvest: 0.65 },
  groundnut: { sowing: 0.4,  vegetative: 0.75, flowering: 1.0,  harvest: 0.6  },
  red_gram:  { sowing: 0.4,  vegetative: 0.7,  flowering: 1.0,  harvest: 0.5  },
}

const SOIL_FC = { light: 25, medium: 35, heavy: 45 }
const SOIL_WP = { light: 10, medium: 18, heavy: 25 }
const ET0_BASE = 5.5

const CROPS = {
  paddy:     'Paddy (వరి)',
  cotton:    'Cotton (పత్తి)',
  groundnut: 'Groundnut (వేరుసెనగ)',
  red_gram:  'Red Gram (కందులు)',
}

const STAGES = {
  sowing: 'Sowing',
  vegetative: 'Vegetative',
  flowering: 'Flowering',
  harvest: 'Harvest',
}

const TEXTURES = {
  light: 'Light',
  medium: 'Medium',
  heavy: 'Heavy',
}

function needColor(mm) {
  if (mm >= 6)  return { bar: 'bg-crimson-600',  text: 'text-crimson-700'  }
  if (mm >= 3)  return { bar: 'bg-amber-500',     text: 'text-amber-700'    }
  return               { bar: 'bg-forest-600',    text: 'text-forest-700'   }
}

function DayCard({ day, etCrop, rainEff, need, volumeL, skipRain }) {
  const { bar, text } = needColor(need)
  const maxMm = 10
  const pct = Math.min(100, (need / maxMm) * 100)

  return (
    <div className={`card p-3 flex flex-col gap-2 ${skipRain ? 'opacity-60' : ''}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-earth-900">{day.day_label}</p>
        {skipRain && (
          <span className="text-[9px] font-semibold bg-forest-100 text-forest-700 px-1.5 py-0.5 rounded-full">
            Skip — rain expected
          </span>
        )}
      </div>

      <div className="flex flex-col gap-1">
        <div className="h-3 bg-earth-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full ${bar} transition-all duration-500`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex justify-between items-center">
          <span className="text-[9px] text-earth-400">0</span>
          <span className={`text-xs font-semibold tabular-nums ${text}`}>{need.toFixed(1)} mm</span>
          <span className="text-[9px] text-earth-400">10mm</span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-1 text-[9px] text-earth-500">
        <div>
          <p className="font-semibold text-earth-700">ET₀ crop</p>
          <p>{etCrop.toFixed(1)} mm</p>
        </div>
        <div>
          <p className="font-semibold text-earth-700">Eff. Rain</p>
          <p>{rainEff.toFixed(1)} mm</p>
        </div>
        <div>
          <p className="font-semibold text-earth-700">Volume</p>
          <p>{Math.round(volumeL).toLocaleString('en-IN')} L</p>
        </div>
      </div>
    </div>
  )
}

function SkeletonCard() {
  return <div className="h-28 bg-earth-100 rounded-2xl animate-pulse" />
}

export default function IrrigationScheduler() {
  const [crop, setCrop] = useState('paddy')
  const [stage, setStage] = useState('vegetative')
  const [soilTexture, setSoilTexture] = useState('medium')
  const [area, setArea] = useState(2)
  const [weather, setWeather] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetchWeatherTiming()
      .then(d => { setWeather(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  const kc = CROP_KC[crop][stage]
  const areaHa = area * 0.405

  const days = weather?.days ?? Array.from({ length: 7 }, (_, i) => ({
    day_label: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i],
    rain_prob: 20,
    rain_mm: 0,
    risk: 'low',
  }))

  const schedule = days.map(d => {
    const et0 = d.rain_prob > 60 ? ET0_BASE * 0.8 : ET0_BASE
    const etCrop = et0 * kc
    const rainEff = (d.rain_mm || 0) * 0.8
    const need = Math.max(0, etCrop - rainEff)
    const volumeL = need * areaHa * 1000
    const skipRain = d.rain_prob > 70
    return { day: d, etCrop, rainEff, need, volumeL, skipRain }
  })

  const totalMm = schedule.reduce((s, d) => s + d.need, 0)
  const totalL = schedule.reduce((s, d) => s + d.volumeL, 0)
  const dripSavingL = totalL * 0.4

  const noWeather = !weather && !loading

  return (
    <div className="flex flex-col gap-6">
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="text-sm font-semibold text-earth-900">7-Day Irrigation Schedule</h2>
            <p className="text-[10px] text-earth-400 mt-0.5">నీటిపారుదల షెడ్యూల్ · Krishna District · ET₀ = {ET0_BASE} mm/day</p>
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

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <p className="section-title mb-2">Growth Stage</p>
                <div className="flex flex-col gap-1.5">
                  {Object.entries(STAGES).map(([k, v]) => (
                    <button
                      key={k}
                      onClick={() => setStage(k)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold text-left transition-all ${
                        stage === k
                          ? 'bg-earth-900 text-white'
                          : 'bg-earth-100 text-earth-600 hover:bg-earth-200'
                      }`}
                    >
                      {v}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="section-title mb-2">Soil Texture</p>
                <div className="flex flex-col gap-1.5">
                  {Object.entries(TEXTURES).map(([k, v]) => (
                    <button
                      key={k}
                      onClick={() => setSoilTexture(k)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold text-left transition-all ${
                        soilTexture === k
                          ? 'bg-earth-700 text-white'
                          : 'bg-earth-100 text-earth-600 hover:bg-earth-200'
                      }`}
                    >
                      {v}
                      <span className="text-[10px] ml-1 opacity-70">FC {SOIL_FC[k]}mm</span>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="section-title mb-2">Area (acres)</p>
                <input
                  type="number"
                  min={0.5}
                  step={0.5}
                  value={area}
                  onChange={e => setArea(Math.max(0.5, parseFloat(e.target.value) || 0.5))}
                  className="field-input"
                />
                <p className="text-[10px] text-earth-400 mt-1.5">Kc = {kc.toFixed(2)} for {STAGES[stage].toLowerCase()}</p>
              </div>
            </div>
          </div>

          {noWeather && (
            <div className="text-xs text-amber-700 bg-amber-100 border border-amber-500/30 rounded-xl px-3 py-2.5">
              Using seasonal ET₀ estimates (5.5 mm/day). Connect to internet for live 7-day forecast.
            </div>
          )}

          <div>
            <p className="section-title mb-3">7-Day Schedule</p>
            {loading ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
                {[1,2,3,4,5,6,7].map(i => <SkeletonCard key={i} />)}
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
                {schedule.map((s, i) => (
                  <DayCard key={i} {...s} />
                ))}
              </div>
            )}
          </div>

          <div className="bg-earth-50 border border-earth-200 rounded-2xl p-4 flex flex-col gap-1">
            <p className="section-title mb-1">Weekly Summary</p>
            <p className="text-sm text-earth-900">
              Total irrigation needed this week:{' '}
              <span className="font-display font-semibold text-forest-900">{totalMm.toFixed(1)} mm</span>
              {' '}
              <span className="text-earth-500">
                ({Math.round(totalL).toLocaleString('en-IN')} litres over {area} acres)
              </span>
            </p>
          </div>

          <div className="bg-amber-100 border border-amber-500/30 rounded-2xl p-4">
            <p className="section-title text-amber-700 mb-1">Efficiency Tip</p>
            <p className="text-sm text-amber-900 mt-1 leading-relaxed">
              Drip irrigation saves 40% water vs flood. At{' '}
              <span className="font-semibold">{Math.round(totalL).toLocaleString('en-IN')} litres/week</span>
              , you save{' '}
              <span className="font-display font-semibold text-amber-700">
                {Math.round(dripSavingL).toLocaleString('en-IN')} litres
              </span>
              {' '}— reducing pumping cost and groundwater draw.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
