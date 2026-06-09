import { useState, useEffect } from 'react'
import { fetchWeatherTiming } from '../../api'

const PESTS = {
  paddy: [
    {
      name: 'Stem Borer', te: 'కాండం తొలుచు పురుగు',
      risk: (w, s) => s === 'vegetative' && w?.avgHumidity > 70 ? 'high' : s === 'vegetative' ? 'medium' : 'low',
      symptom: 'Dead heart / White ear',
      action: 'Spray Chlorpyriphos 2ml/L or Carbofuran 3G @ 25kg/ha',
      preventive: 'Light traps, remove egg masses',
    },
    {
      name: 'Rice Blast', te: 'వరి బ్లాస్ట్',
      risk: (w, s) => w?.avgRain > 3 && s !== 'harvest' ? 'high' : w?.avgRain > 1 ? 'medium' : 'low',
      symptom: 'Diamond-shaped lesions on leaves',
      action: 'Spray Tricyclazole 0.6g/L or Isoprothiolane 1.5ml/L',
      preventive: 'Use resistant varieties, balanced N',
    },
    {
      name: 'BPH (Brown Planthopper)', te: 'గోధుమ రంగు అడుగు తొలుచు పురుగు',
      risk: (w, s) => w?.avgHumidity > 80 ? 'high' : 'low',
      symptom: 'Hopper burn, lodging',
      action: 'Spray Buprofezin 25SC 1ml/L. Drain water for 2-3 days',
      preventive: 'Avoid excess N, use light traps',
    },
  ],
  cotton: [
    {
      name: 'Bollworm', te: 'పత్తి కాయ తొలుచు పురుగు',
      risk: (w, s) => s === 'flowering' && w?.avgTemp > 28 ? 'high' : s === 'flowering' ? 'medium' : 'low',
      symptom: 'Entry holes in bolls, frass',
      action: 'Spray Emamectin Benzoate 0.4g/L or Spinosad 0.3ml/L',
      preventive: 'Pheromone traps, timely sowing',
    },
    {
      name: 'Whitefly', te: 'తెల్ల పురుగు',
      risk: (w, s) => w?.avgTemp > 30 && w?.avgHumidity < 60 ? 'high' : 'medium',
      symptom: 'Leaf curl, honeydew, sooty mold',
      action: 'Spray Imidacloprid 0.3ml/L or Thiamethoxam 0.2g/L',
      preventive: 'Yellow sticky traps, neem spray',
    },
    {
      name: 'Aphid', te: 'పేను పురుగు',
      risk: (w, s) => w?.avgTemp > 25 ? 'medium' : 'low',
      symptom: 'Curled leaves, sticky honeydew',
      action: 'Spray Dimethoate 2ml/L or release Chrysoperla',
      preventive: 'Monitor with suction traps',
    },
  ],
  groundnut: [
    {
      name: 'Leaf Miner', te: 'ఆకు తొలుచు పురుగు',
      risk: (w, s) => w?.avgHumidity < 60 ? 'high' : 'medium',
      symptom: 'Serpentine mines on leaves',
      action: 'Spray Spinosad 0.3ml/L or Dimethoate 1.7ml/L',
      preventive: 'Remove and destroy affected leaves',
    },
    {
      name: 'Tikka (Leaf Spot)', te: 'తిక్కా వ్యాధి',
      risk: (w, s) => w?.avgRain > 2 ? 'high' : 'low',
      symptom: 'Brown/black spots with yellow halo',
      action: 'Spray Mancozeb 2.5g/L or Carbendazim 1g/L',
      preventive: 'Seed treatment, crop rotation',
    },
    {
      name: 'Termite', te: 'చెదపురుగు',
      risk: (w, s) => s === 'sowing' ? 'medium' : 'low',
      symptom: 'Plant wilting, root damage',
      action: 'Drench Chlorpyriphos 4ml/L around root zone',
      preventive: 'FYM application, avoid crop residue',
    },
  ],
  red_gram: [
    {
      name: 'Pod Borer', te: 'కాయ తొలుచు పురుగు',
      risk: (w, s) => s === 'flowering' || s === 'harvest' ? 'high' : 'low',
      symptom: 'Entry holes in pods, frass',
      action: 'Spray Ha-NPV 250 LE/ha or Indoxacarb 0.7ml/L',
      preventive: 'Intercrop with sorghum, pheromone traps',
    },
    {
      name: 'Wilt (Fusarium)', te: 'వాడు వ్యాధి',
      risk: (w, s) => w?.avgTemp > 28 ? 'medium' : 'low',
      symptom: 'Sudden wilting, brown vascular tissue',
      action: 'No cure — remove and destroy plants. Drench with Carbendazim',
      preventive: 'Use resistant varieties, Trichoderma seed treatment',
    },
  ],
}

const CROPS = {
  paddy: 'Paddy (వరి)',
  cotton: 'Cotton (పత్తి)',
  groundnut: 'Groundnut (వేరుసెనగ)',
  red_gram: 'Red Gram (కందులు)',
}

const STAGES = {
  sowing: 'Sowing',
  vegetative: 'Vegetative',
  flowering: 'Flowering',
  harvest: 'Harvest',
}

const RISK_STYLES = {
  high:   { border: 'border-l-crimson-600',  badge: 'bg-crimson-100 text-crimson-700', label: 'High Risk'   },
  medium: { border: 'border-l-amber-500',    badge: 'bg-amber-100 text-amber-700',     label: 'Medium Risk' },
  low:    { border: 'border-l-forest-600',   badge: 'bg-forest-100 text-forest-700',   label: 'Low Risk'    },
}

function deriveWeatherStats(days) {
  if (!days || days.length === 0) return null
  const avgRainProb = days.reduce((s, d) => s + (d.rain_prob || 0), 0) / days.length
  const avgRain = days.reduce((s, d) => s + (d.rain_mm || 0), 0) / days.length
  const avgTemp = 28 + (avgRainProb > 60 ? -2 : 2)
  const avgHumidity = Math.round(40 + avgRainProb * 0.5)
  return { avgTemp, avgHumidity, avgRain }
}

export default function PestAlert() {
  const [crop, setCrop] = useState('paddy')
  const [stage, setStage] = useState('vegetative')
  const [weather, setWeather] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetchWeatherTiming()
      .then(d => { setWeather(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [crop])

  const stats = weather?.days ? deriveWeatherStats(weather.days) : null

  const pests = PESTS[crop] || []

  return (
    <div className="flex flex-col gap-6">
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="text-sm font-semibold text-earth-900">Pest & Disease Alert</h2>
            <p className="text-[10px] text-earth-400 mt-0.5">కీట రోగ హెచ్చరిక · Early warning system</p>
          </div>
        </div>

        <div className="p-5 flex flex-col gap-5">
          <div className="flex flex-col gap-3">
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

            <div>
              <p className="section-title mb-2">Growth Stage</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(STAGES).map(([k, v]) => (
                  <button
                    key={k}
                    onClick={() => setStage(k)}
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                      stage === k
                        ? 'bg-earth-900 text-white shadow-sm'
                        : 'bg-earth-100 text-earth-600 hover:bg-earth-200'
                    }`}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            {loading ? (
              [1, 2, 3].map(i => (
                <div key={i} className="h-14 bg-earth-100 rounded-xl animate-pulse" />
              ))
            ) : stats ? (
              <>
                <div className="bg-earth-50 border border-earth-200 rounded-xl px-3 py-2.5 text-center">
                  <p className="section-title">Avg Temp</p>
                  <p className="font-display text-lg font-semibold text-earth-900 mt-0.5">{stats.avgTemp}°C</p>
                </div>
                <div className="bg-earth-50 border border-earth-200 rounded-xl px-3 py-2.5 text-center">
                  <p className="section-title">Avg Humidity</p>
                  <p className="font-display text-lg font-semibold text-earth-900 mt-0.5">~{stats.avgHumidity}%</p>
                </div>
                <div className="bg-earth-50 border border-earth-200 rounded-xl px-3 py-2.5 text-center">
                  <p className="section-title">Rain Forecast</p>
                  <p className="font-display text-lg font-semibold text-earth-900 mt-0.5">~{stats.avgRain.toFixed(1)}mm</p>
                </div>
              </>
            ) : (
              <div className="col-span-3 text-xs text-earth-500 bg-amber-100 border border-amber-500/30 rounded-xl px-3 py-2.5">
                Weather data unavailable — showing seasonal risk only
              </div>
            )}
          </div>

          <div className="flex flex-col gap-3">
            <p className="section-title">Pest Risk Assessment</p>
            {pests.map((pest) => {
              const riskLevel = pest.risk(stats, stage)
              const rs = RISK_STYLES[riskLevel] || RISK_STYLES.low
              return (
                <div
                  key={pest.name}
                  className={`bg-white border border-earth-200 border-l-4 ${rs.border} rounded-2xl p-4 flex flex-col gap-2 shadow-sm`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-earth-900">{pest.name}</p>
                      <p className="text-[10px] text-earth-400 mt-0.5">{pest.te}</p>
                    </div>
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full shrink-0 ${rs.badge}`}>
                      {rs.label}
                    </span>
                  </div>

                  <p className="text-xs text-earth-500">
                    <span className="font-semibold text-earth-700">Symptom: </span>
                    {pest.symptom}
                  </p>

                  <div className="bg-forest-100 border border-forest-300 rounded-xl px-3 py-2">
                    <p className="text-[10px] font-semibold text-forest-700 uppercase tracking-wider mb-0.5">Recommended Action</p>
                    <p className="text-xs text-forest-800">{pest.action}</p>
                  </div>

                  <p className="text-[10px] text-earth-500">
                    <span className="font-semibold">Prevention: </span>
                    {pest.preventive}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
