const T = {
  en: {
    npk:       'NPK Application Schedule',
    micro:     'Micronutrient Corrections',
    no_micro:  'No micronutrient deficiencies detected.',
    no_macro:  'Soil nutrient levels adequate — no macronutrient application needed.',
    nutrient:  'Nutrient', timing: 'Timing', kg_ha: 'kg / ha', kg_acre: 'kg / acre',
    deficiency:'deficiency', apply: 'Apply',
    savings:   (n, area) => `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })} estimated savings vs. blanket application for ${area} acres`,
    acres:     'acres', target: 'Target',
  },
  te: {
    npk:       'NPK వేసే సమయపట్టిక',
    micro:     'సూక్ష్మ పోషక దిద్దుబాట్లు',
    no_micro:  'సూక్ష్మ పోషక లోపాలు లేవు.',
    no_macro:  'పోషక స్థాయిలు తగినవి — స్థూల పోషక దరఖాస్తు అవసరం లేదు.',
    nutrient:  'పోషకం', timing: 'సమయం', kg_ha: 'kg/హెక్టారు', kg_acre: 'kg/ఎకరం',
    deficiency:'లోపం', apply: 'వేయండి',
    savings:   (n, area) => `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })} ${area} ఎకరాలకు అంచనా ఆదా`,
    acres:     'ఎకరాలు', target: 'లక్ష్యం',
  },
}

function NPKCard({ nutrient, dose }) {
  const intensity = dose === 0 ? 'low' : dose < 60 ? 'med' : 'high'
  const styles = {
    low:  'bg-forest-900   text-white      border-forest-700',
    med:  'bg-terra-600    text-white      border-terra-500',
    high: 'bg-crimson-600  text-white      border-crimson-500',
  }
  return (
    <div className={`rounded-2xl border p-4 text-center ${styles[intensity]} flex flex-col items-center`}>
      <p className="text-xs font-semibold uppercase tracking-widest opacity-70 mb-1">{nutrient}</p>
      <p className="font-display text-[2.8rem] font-semibold leading-none">{dose.toFixed(0)}</p>
      <p className="text-xs opacity-60 mt-1">kg / ha</p>
    </div>
  )
}

export default function RecommendationOutput({ rec, cropName, area, targetYield, lang }) {
  const str = T[lang] ?? T.en

  if (!rec) {
    return (
      <div className="h-full min-h-64 flex flex-col items-center justify-center card p-10 text-center gap-4">
        <div className="w-14 h-14 rounded-2xl bg-earth-100 flex items-center justify-center">
          <svg className="w-7 h-7 text-earth-400" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 3C6.5 3 2 7.5 2 13a10 10 0 0 0 10 10c5.52 0 10-4.48 10-10 0-5.52-4.48-10-10-10m-1 17.93V19c0-.55.45-1 1-1s1 .45 1 1v1.93c-2.65-.47-4.83-2.29-5.72-4.72L9 16.5c.09-.01.18-.01.27-.01A2.74 2.74 0 0 0 12 13.75c0-1.52-1.23-2.75-2.75-2.75-1.37 0-2.52.99-2.72 2.33L5.07 13c.47-2.65 2.29-4.83 4.72-5.72L9.5 9c.01.09.01.18.01.27A2.74 2.74 0 0 0 12.25 12c1.52 0 2.75-1.23 2.75-2.75 0-1.37-.99-2.52-2.33-2.72L13 5.07c2.65.47 4.83 2.29 5.72 4.72L17 9.5c-.09.01-.18.01-.27.01A2.74 2.74 0 0 0 14 12.25c0 1.52 1.23 2.75 2.75 2.75 1.37 0 2.52-.99 2.72-2.33L20.93 13c-.47 2.65-2.29 4.83-4.72 5.72L15.5 17a.74.74 0 0 1-.27-.01A2.74 2.74 0 0 0 12.5 14.75c-1.52 0-2.75 1.23-2.75 2.75 0 1.37.99 2.52 2.33 2.72L11 21c-.34-.03-.67-.07-1-.07z"/>
          </svg>
        </div>
        <div>
          <p className="font-semibold text-earth-800 text-sm">Enter field details</p>
          <p className="text-xs text-earth-500 mt-1">Fill in the form and click <strong>Generate Recommendation</strong></p>
        </div>
      </div>
    )
  }

  const macros  = Object.entries(rec.macronutrients ?? {})
  const micros  = rec.micronutrients ?? []
  const savings = rec.estimated_savings_inr ?? 0

  // Build split schedule rows
  const rows = []
  for (const [nutrient, r] of macros) {
    for (const split of r.splits ?? []) {
      rows.push({ nutrient, timing: split.timing, kg_ha: split.dose_kg_ha, kg_acre: (split.dose_kg_ha * 0.4047).toFixed(1) })
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Banner */}
      <div className="card px-5 py-4 flex items-center gap-3 bg-forest-50 border-forest-200">
        <div className="w-8 h-8 rounded-full bg-forest-900 flex items-center justify-center shrink-0">
          <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
          </svg>
        </div>
        <div>
          <p className="text-sm font-semibold text-forest-900">{cropName}</p>
          <p className="text-xs text-earth-500">
            {area} {str.acres} · {str.target} {targetYield} t/ha
          </p>
        </div>
      </div>

      {/* N / P / K dose cards */}
      <div className="grid grid-cols-3 gap-3">
        {macros.map(([nutrient, r]) => (
          <NPKCard key={nutrient} nutrient={nutrient} dose={r.dose_kg_ha} />
        ))}
      </div>

      {/* NPK schedule table */}
      <div className="card overflow-hidden">
        <div className="card-header">
          <h3 className="text-xs font-semibold text-earth-700 uppercase tracking-widest">{str.npk}</h3>
        </div>
        {rows.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-earth-50 border-b border-earth-100">
                  {[str.nutrient, str.timing, str.kg_ha, str.kg_acre].map(h => (
                    <th key={h} className="px-4 py-2.5 text-left text-[10px] font-semibold text-earth-500 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-earth-50">
                {rows.map((row, i) => (
                  <tr key={i} className="hover:bg-earth-50/50">
                    <td className="px-4 py-2.5 font-semibold text-forest-900">{row.nutrient}</td>
                    <td className="px-4 py-2.5 text-earth-600 text-xs">{row.timing}</td>
                    <td className="px-4 py-2.5 font-display text-base text-earth-900">{row.kg_ha.toFixed(1)}</td>
                    <td className="px-4 py-2.5 text-earth-500 text-xs tabular-nums">{row.kg_acre}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="px-4 py-3 text-sm text-forest-700 bg-forest-50">{str.no_macro}</p>
        )}
      </div>

      {/* Micronutrient corrections */}
      <div className="card overflow-hidden">
        <div className="card-header">
          <h3 className="text-xs font-semibold text-earth-700 uppercase tracking-widest">{str.micro}</h3>
        </div>
        <div className="p-4 flex flex-col gap-2.5">
          {micros.length === 0 ? (
            <div className="flex items-center gap-2.5 bg-forest-50 border border-forest-200 rounded-xl px-4 py-3 text-sm text-forest-800">
              <svg className="w-4 h-4 shrink-0 text-forest-600" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
              </svg>
              {str.no_micro}
            </div>
          ) : micros.map((m, i) => (
            <div key={i} className="flex items-start gap-3 bg-amber-100 border border-amber-300 rounded-xl px-4 py-3">
              <svg className="w-4 h-4 mt-0.5 shrink-0 text-amber-700" viewBox="0 0 24 24" fill="currentColor">
                <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/>
              </svg>
              <div className="text-sm">
                <p className="font-semibold text-amber-900">
                  {m.nutrient} {str.deficiency} —{' '}
                  <span className="font-normal">
                    {str.apply} {m.carrier}: <strong>{m.dose_kg_ha} kg/ha</strong> ({m.dose_kg_acre} kg/acre).
                  </span>
                </p>
                <p className="text-xs text-amber-700 mt-0.5 font-medium">{m.timing}</p>
                {m.foliar && <p className="text-xs text-amber-600 mt-0.5 italic">{m.foliar}</p>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Savings */}
      {savings > 0 && (
        <div className="flex items-center gap-3 card px-5 py-4 border-amber-200 bg-amber-50">
          <div className="w-8 h-8 rounded-full bg-amber-500 flex items-center justify-center shrink-0">
            <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
              <path d="M11.8 10.9c-2.27-.59-3-1.2-3-2.15 0-1.09 1.01-1.85 2.7-1.85 1.78 0 2.44.85 2.5 2.1h2.21c-.07-1.72-1.12-3.3-3.21-3.81V3h-3v2.16c-1.94.42-3.5 1.68-3.5 3.61 0 2.31 1.91 3.46 4.7 4.13 2.5.6 3 1.48 3 2.41 0 .69-.49 1.79-2.7 1.79-2.06 0-2.87-.92-2.98-2.1h-2.2c.12 2.19 1.76 3.42 3.68 3.83V21h3v-2.15c1.95-.37 3.5-1.5 3.5-3.55 0-2.84-2.43-3.81-4.7-4.4z"/>
            </svg>
          </div>
          <p className="text-sm font-semibold text-amber-900">{str.savings(savings, area)}</p>
        </div>
      )}
    </div>
  )
}
