import { useState } from 'react'

const PRACTICES = {
  compost:     { name: 'Compost / FYM',  te: 'కంపోస్ట్',     icon: '🌾', ocGainPerYear: 0.08, cost: 3000,  description: 'Apply 5-6 t/ha FYM annually. Improves soil structure and water retention.' },
  greenManure: { name: 'Green Manure',   te: 'పచ్చిరొట్ట',    icon: '🌿', ocGainPerYear: 0.06, cost: 1800,  description: 'Grow Dhaincha or Sunhemp, incorporate before flowering. Also fixes N.' },
  zeroTillage: { name: 'Zero Tillage',   te: 'నిర్-దుక్కి',   icon: '🚜', ocGainPerYear: 0.05, cost: -1200, description: 'Avoid ploughing — conserves soil carbon. Reduces fuel cost by ₹1,200/ha.' },
  biochar:     { name: 'Biochar',        te: 'బయోఛార్',       icon: '🔥', ocGainPerYear: 0.12, cost: 8000,  description: 'Apply 2 t/ha biochar. Permanent carbon sink, lasts 100+ years.' },
}

const OC_TO_CO2 = 14.85

function fmt(n) {
  return Math.abs(n) >= 1000
    ? '₹' + Math.round(n).toLocaleString('en-IN')
    : '₹' + Math.round(n)
}

export default function CarbonCredits() {
  const [area, setArea] = useState(5)
  const [currentOC, setCurrentOC] = useState(0.45)
  const [targetOC, setTargetOC] = useState(0.75)
  const [practice, setPractice] = useState('compost')
  const [carbonPrice, setCarbonPrice] = useState(500)

  const p = PRACTICES[practice]
  const area_ha = area * 0.405
  const deltaOC = Math.max(0, targetOC - currentOC)
  const total_CO2 = deltaOC * OC_TO_CO2 * area_ha
  const years = deltaOC > 0 ? deltaOC / p.ocGainPerYear : 0
  const annual_CO2 = years > 0 ? total_CO2 / years : 0
  const annual_revenue = annual_CO2 * carbonPrice
  const annual_cost = p.cost * area_ha
  const net_annual = annual_revenue - annual_cost
  const cop29Revenue = annual_CO2 * 2500

  const revenueBarPct = annual_cost > 0 ? Math.min(100, (annual_revenue / Math.max(annual_revenue, annual_cost)) * 100) : 100
  const costBarPct = annual_revenue > 0 ? Math.min(100, (annual_cost / Math.max(annual_revenue, annual_cost)) * 100) : 100

  return (
    <div className="flex flex-col gap-6">
      <div className="card">
        <div className="card-header">
          <span className="text-base mr-2">🌿</span>
          <span className="font-semibold text-earth-900">Carbon Credit Estimator</span>
          <span className="ml-2 text-[10px] text-earth-500">కార్బన్ క్రెడిట్స్</span>
        </div>
        <div className="px-5 py-5 flex flex-col gap-6">
          <div>
            <span className="section-title">Select Practice</span>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-2">
              {Object.entries(PRACTICES).map(([key, pr]) => (
                <button
                  key={key}
                  onClick={() => setPractice(key)}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    practice === key
                      ? 'bg-green-900 border-green-900 text-white'
                      : 'bg-white border-earth-200 text-earth-700 hover:border-green-600'
                  }`}
                >
                  <div className="text-xl mb-1">{pr.icon}</div>
                  <div className="text-xs font-semibold leading-tight">{pr.name}</div>
                  <div className={`text-[9px] mt-0.5 ${practice === key ? 'text-green-200' : 'text-earth-400'}`}>{pr.te}</div>
                  <div className={`text-[10px] mt-2 font-medium ${practice === key ? 'text-green-100' : 'text-green-700'}`}>
                    +{pr.ocGainPerYear}% OC/yr
                  </div>
                  <div className={`text-[9px] ${practice === key ? 'text-green-200' : 'text-earth-500'}`}>
                    {pr.cost < 0 ? `Saves ₹${Math.abs(pr.cost)}/ha` : `₹${pr.cost}/ha cost`}
                  </div>
                </button>
              ))}
            </div>
            <p className="text-xs text-earth-500 mt-2 italic">{p.description}</p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <div className="flex flex-col gap-4">
              <div>
                <label className="section-title block mb-1">Area: {area} acres ({(area * 0.405).toFixed(1)} ha)</label>
                <input type="range" min={1} max={50} step={0.5} value={area}
                  onChange={e => setArea(Number(e.target.value))}
                  className="w-full accent-green-700" />
                <div className="flex justify-between text-[10px] text-earth-400 mt-0.5">
                  <span>1 acre</span><span>50 acres</span>
                </div>
              </div>
              <div>
                <label className="section-title block mb-1">Current OC: {currentOC.toFixed(2)}%</label>
                <input type="range" min={0.2} max={2.0} step={0.05} value={currentOC}
                  onChange={e => {
                    const v = Number(e.target.value)
                    setCurrentOC(v)
                    if (targetOC <= v) setTargetOC(Math.min(2.5, v + 0.1))
                  }}
                  className="w-full accent-amber-500" />
                <div className="flex justify-between text-[10px] text-earth-400 mt-0.5">
                  <span>0.20%</span><span>2.0%</span>
                </div>
              </div>
              <div>
                <label className="section-title block mb-1">Target OC: {targetOC.toFixed(2)}%</label>
                <input type="range" min={Math.min(2.5, currentOC + 0.1)} max={2.5} step={0.05} value={targetOC}
                  onChange={e => setTargetOC(Number(e.target.value))}
                  className="w-full accent-green-600" />
                <div className="flex justify-between text-[10px] text-earth-400 mt-0.5">
                  <span>{(currentOC + 0.1).toFixed(2)}%</span><span>2.5%</span>
                </div>
              </div>
              <div>
                <label className="section-title block mb-1">Carbon Price: ₹{carbonPrice}/tonne CO₂</label>
                <input type="range" min={200} max={2000} step={50} value={carbonPrice}
                  onChange={e => setCarbonPrice(Number(e.target.value))}
                  className="w-full accent-earth-600" />
                <div className="flex justify-between text-[10px] text-earth-400 mt-0.5">
                  <span>₹200</span><span>₹2,000</span>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <div className="text-center py-4 bg-green-50 rounded-2xl border border-green-100">
                <div className="section-title text-green-700 mb-1">Annual Carbon Income</div>
                <div className="font-display text-4xl font-bold text-green-800">
                  {fmt(annual_revenue)}
                </div>
                <div className="text-xs text-green-600 mt-1">per year</div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div className="bg-earth-50 rounded-xl p-3 text-center">
                  <div className="section-title mb-1">CO₂ Sequestered</div>
                  <div className="font-display text-xl font-semibold text-earth-800">{annual_CO2.toFixed(1)}</div>
                  <div className="text-[9px] text-earth-500">t/year</div>
                </div>
                <div className="bg-earth-50 rounded-xl p-3 text-center">
                  <div className="section-title mb-1">Time to Target</div>
                  <div className="font-display text-xl font-semibold text-earth-800">{years.toFixed(1)}</div>
                  <div className="text-[9px] text-earth-500">years</div>
                </div>
                <div className={`rounded-xl p-3 text-center ${net_annual >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                  <div className="section-title mb-1">Net Benefit</div>
                  <div className={`font-display text-xl font-semibold ${net_annual >= 0 ? 'text-green-800' : 'text-red-700'}`}>
                    {fmt(net_annual)}
                  </div>
                  <div className={`text-[9px] ${net_annual >= 0 ? 'text-green-600' : 'text-red-500'}`}>/year</div>
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-earth-500 w-16 text-right shrink-0">Revenue</span>
                  <div className="flex-1 bg-earth-100 rounded-full h-3 overflow-hidden">
                    <div className="h-full bg-green-500 rounded-full transition-all duration-500" style={{ width: `${revenueBarPct}%` }} />
                  </div>
                  <span className="text-[10px] text-green-700 font-semibold w-20 shrink-0">{fmt(annual_revenue)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-earth-500 w-16 text-right shrink-0">Cost</span>
                  <div className="flex-1 bg-earth-100 rounded-full h-3 overflow-hidden">
                    <div className={`h-full rounded-full transition-all duration-500 ${annual_cost < 0 ? 'bg-green-400' : 'bg-amber-400'}`} style={{ width: `${costBarPct}%` }} />
                  </div>
                  <span className={`text-[10px] font-semibold w-20 shrink-0 ${annual_cost < 0 ? 'text-green-600' : 'text-amber-700'}`}>
                    {annual_cost < 0 ? `+${fmt(Math.abs(annual_cost))}` : fmt(annual_cost)}
                  </span>
                </div>
              </div>

              {net_annual < 0 && annual_revenue > 0 && (
                <div className="text-[10px] text-amber-700 bg-amber-50 px-3 py-2 rounded-xl border border-amber-100">
                  Payback period: {(annual_cost / annual_revenue).toFixed(1)} years to break even
                </div>
              )}
            </div>
          </div>

          <div className="bg-green-900 text-white rounded-2xl px-5 py-4 flex flex-col gap-1">
            <div className="text-[10px] font-semibold text-green-300 uppercase tracking-wider">COP29 Scenario</div>
            <p className="text-xs text-green-100">
              At COP29 targets, carbon prices could reach ₹2,500/tonne by 2030 — your potential revenue:{' '}
              <span className="font-display text-base font-bold text-white">{fmt(cop29Revenue)}/year</span>
            </p>
          </div>

          <div className="flex items-start gap-2 text-[11px] text-earth-500 bg-earth-50 rounded-xl px-4 py-3 border border-earth-100">
            <span className="mt-0.5">ℹ</span>
            <span>Carbon credits require third-party verification (Verra/Gold Standard). Estimated values only.</span>
          </div>
        </div>
      </div>
    </div>
  )
}
