import { useState } from 'react'
import { postRecommendation, CROPS, DEFAULT_YIELDS } from '../../api'
import RecommendationOutput from './RecommendationOutput'
import CropSuitability from './CropSuitability'
import WeatherTiming from './WeatherTiming'

const MACRO_SLIDERS = [
  { id: 'pH', label: 'pH', unit: '',      min: 4.0, max: 10.0, step: 0.1,  def: 6.8,  marks: [4, 5.5, 6.5, 7.5, 10] },
  { id: 'EC', label: 'EC', unit: 'dS/m', min: 0,   max: 6.0,  step: 0.1,  def: 0.4,  marks: [0, 1, 2, 4, 6] },
  { id: 'OC', label: 'OC', unit: '%',    min: 0,   max: 2.5,  step: 0.05, def: 0.45, marks: [0, 0.5, 1.0, 2.5] },
  { id: 'N',  label: 'N',  unit: 'kg/ha',min: 0,   max: 800,  step: 10,   def: 200,  marks: [0, 280, 560, 800] },
  { id: 'P',  label: 'P',  unit: 'kg/ha',min: 0,   max: 80,   step: 1,    def: 18,   marks: [0, 11, 22, 80] },
  { id: 'K',  label: 'K',  unit: 'kg/ha',min: 0,   max: 600,  step: 10,   def: 150,  marks: [0, 110, 280, 600] },
]

const MICRO_FIELDS = [
  { id: 'Zn', label: 'Zinc',   unit: 'ppm', def: 0.4,  step: 0.1  },
  { id: 'Fe', label: 'Iron',   unit: 'ppm', def: 3.5,  step: 0.5  },
  { id: 'B',  label: 'Boron',  unit: 'ppm', def: 0.3,  step: 0.1  },
  { id: 'Cu', label: 'Copper', unit: 'ppm', def: 0.15, step: 0.05 },
]

function Divider({ label }) {
  return (
    <div className="flex items-center gap-3 py-1">
      <div className="flex-1 h-px bg-earth-100" />
      <span className="text-[10px] font-semibold text-earth-400 uppercase tracking-widest whitespace-nowrap">{label}</span>
      <div className="flex-1 h-px bg-earth-100" />
    </div>
  )
}

function SliderField({ id, label, unit, min, max, step, marks, value, onChange }) {
  const pct = ((value - min) / (max - min)) * 100
  return (
    <div className="mb-4">
      <div className="flex justify-between items-center mb-2">
        <label className="text-xs font-semibold text-earth-700">
          {label}
          {unit && <span className="text-earth-400 font-normal ml-1">({unit})</span>}
        </label>
        <span className="font-display text-base font-semibold text-forest-900 tabular-nums">{value}</span>
      </div>
      <div className="relative">
        <div className="absolute inset-y-0 left-0 flex items-center pointer-events-none">
          <div
            className="h-1 rounded-l-full bg-forest-700"
            style={{ width: `${pct}%` }}
          />
        </div>
        <input
          type="range" min={min} max={max} step={step} value={value}
          onChange={e => onChange(id, parseFloat(e.target.value))}
        />
      </div>
      <div className="flex justify-between mt-1">
        {marks.map(m => (
          <span key={m} className="text-[9px] text-earth-400 tabular-nums">{m}</span>
        ))}
      </div>
    </div>
  )
}

export default function FarmerAdvisory() {
  const [lang,    setLang]    = useState('en')
  const [crop,    setCrop]    = useState('paddy')
  const [area,    setArea]    = useState(2.0)
  const [yld,     setYld]     = useState(DEFAULT_YIELDS.paddy)
  const [loading, setLoading] = useState(false)
  const [rec,     setRec]     = useState(null)
  const [error,   setError]   = useState(null)

  const [macros, setMacros] = useState(
    Object.fromEntries(MACRO_SLIDERS.map(s => [s.id, s.def]))
  )
  const [micros, setMicros] = useState(
    Object.fromEntries(MICRO_FIELDS.map(f => [f.id, f.def]))
  )

  function handleCropChange(c) {
    setCrop(c)
    setYld(DEFAULT_YIELDS[c])
  }

  async function handleSubmit() {
    setLoading(true)
    setError(null)
    try {
      const result = await postRecommendation({
        crop, area_acres: area, target_yield: yld,
        soil: { ...macros, ...micros },
      })
      setRec(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const cropNameTe = { paddy: 'వరి', cotton: 'పత్తి', groundnut: 'వేరుసెనగ', red_gram: 'కందులు' }
  const cropName   = lang === 'te' ? cropNameTe[crop] : CROPS[crop]

  const soilForSuitability = { ...macros, ...micros }

  return (
    <div className="flex flex-col gap-6">

      {/* ── Top row: Crop Suitability + Weather Timing ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3">
          <CropSuitability soil={soilForSuitability} lang={lang} />
        </div>
        <div className="lg:col-span-2">
          <WeatherTiming />
        </div>
      </div>

      {/* ── Bottom row: Input form + Recommendation output ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      {/* ── Left: Input form ── */}
      <div className="lg:col-span-2 card">
        {/* Header */}
        <div className="card-header justify-between">
          <div>
            <h2 className="text-sm font-semibold text-earth-900">Field Details</h2>
            <p className="text-[10px] text-earth-400 mt-0.5">పొలం వివరాలు</p>
          </div>
          {/* Lang toggle */}
          <div className="flex bg-earth-100 rounded-lg p-0.5">
            {[['en', 'EN'], ['te', 'తెలుగు']].map(([v, l]) => (
              <button
                key={v}
                onClick={() => setLang(v)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                  lang === v
                    ? 'bg-white shadow-sm text-forest-900'
                    : 'text-earth-500 hover:text-earth-700'
                }`}
              >
                {l}
              </button>
            ))}
          </div>
        </div>

        <div className="p-5 flex flex-col gap-5">
          {/* Crop + area */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="section-title block mb-1.5">Crop</label>
              <select
                value={crop} onChange={e => handleCropChange(e.target.value)}
                className="field-input"
              >
                {Object.entries(CROPS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="section-title block mb-1.5">Area (acres)</label>
              <input
                type="number" min={0.5} step={0.5} value={area}
                onChange={e => setArea(parseFloat(e.target.value))}
                className="field-input"
              />
            </div>
          </div>

          <div>
            <label className="section-title block mb-1.5">Target yield (t/ha)</label>
            <input
              type="number" min={0.5} step={0.5} value={yld}
              onChange={e => setYld(parseFloat(e.target.value))}
              className="field-input"
            />
          </div>

          <Divider label="Macronutrients" />
          {MACRO_SLIDERS.map(s => (
            <SliderField
              key={s.id} {...s}
              value={macros[s.id]}
              onChange={(id, val) => setMacros(p => ({ ...p, [id]: val }))}
            />
          ))}

          <Divider label="Micronutrients · ppm" />
          <div className="grid grid-cols-2 gap-3">
            {MICRO_FIELDS.map(f => (
              <div key={f.id}>
                <label className="section-title block mb-1.5">
                  {f.label}
                  <span className="text-earth-400 font-normal normal-case tracking-normal ml-1">({f.unit})</span>
                </label>
                <input
                  type="number" min={0} step={f.step} value={micros[f.id]}
                  onChange={e => setMicros(p => ({ ...p, [f.id]: parseFloat(e.target.value) || 0 }))}
                  className="field-input"
                />
              </div>
            ))}
          </div>

          {error && (
            <div className="flex items-start gap-2 text-xs text-crimson-700 bg-crimson-100 border border-crimson-200 rounded-xl px-3 py-2.5">
              <svg className="w-3.5 h-3.5 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
              </svg>
              {error}
            </div>
          )}

          <button
            onClick={handleSubmit} disabled={loading}
            className="w-full flex items-center justify-center gap-2.5 bg-forest-900 hover:bg-forest-800 disabled:opacity-60 text-white font-semibold text-sm py-3.5 rounded-xl transition-all duration-200 shadow-sm hover:shadow-md"
          >
            {loading ? (
              <div className="w-4 h-4 rounded-full border-2 border-white/40 border-t-white animate-spin" />
            ) : (
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/>
              </svg>
            )}
            {lang === 'te' ? 'సిఫార్సు పొందండి' : 'Generate Recommendation'}
          </button>
        </div>
      </div>

      {/* ── Right: Output ── */}
      <div className="lg:col-span-3">
        <RecommendationOutput
          rec={rec} cropName={cropName}
          area={area} targetYield={yld} lang={lang}
        />
      </div>
      </div>
    </div>
  )
}
