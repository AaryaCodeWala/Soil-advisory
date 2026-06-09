import { useState, useMemo } from 'react'

const CROP_DATA = {
  paddy:     { name: 'Paddy (వరి)',          msp: 2183, baseYield: 4.5, optYield: 5.5, fertCost: 4200,  laborCost: 8000,  harvestCost: 3500 },
  cotton:    { name: 'Cotton (పత్తి)',        msp: 6620, baseYield: 1.5, optYield: 2.0, fertCost: 5800,  laborCost: 12000, harvestCost: 4000 },
  groundnut: { name: 'Groundnut (వేరుసెనగ)', msp: 6377, baseYield: 2.0, optYield: 2.5, fertCost: 3800,  laborCost: 9000,  harvestCost: 3200 },
  red_gram:  { name: 'Red Gram (కందులు)',    msp: 7000, baseYield: 1.0, optYield: 1.4, fertCost: 2800,  laborCost: 7000,  harvestCost: 2500 },
}

function calcRevenue(yieldTha, price) {
  return yieldTha * 0.405 * 10 * price
}

function fmt(n) {
  return '₹' + Math.round(n).toLocaleString('en-IN')
}

function BarComparison({ label, baseRev, baseCost, optRev, optCost }) {
  const max = Math.max(baseRev, baseCost, optRev, optCost, 1)
  const bars = [
    { label: 'Base Revenue',  value: baseRev,  color: 'bg-forest-400' },
    { label: 'Base Cost',     value: baseCost,  color: 'bg-amber-500'  },
    { label: 'Opt. Revenue',  value: optRev,   color: 'bg-forest-700' },
    { label: 'Opt. Cost',     value: optCost,   color: 'bg-amber-700'  },
  ]
  return (
    <div className="flex flex-col gap-2">
      {bars.map(b => (
        <div key={b.label} className="flex items-center gap-3">
          <span className="text-[10px] text-earth-500 w-24 shrink-0">{b.label}</span>
          <div className="flex-1 h-5 bg-earth-100 rounded-lg overflow-hidden">
            <div
              className={`h-full rounded-lg ${b.color} transition-all duration-500`}
              style={{ width: `${(b.value / max) * 100}%` }}
            />
          </div>
          <span className="text-[10px] font-semibold text-earth-700 tabular-nums w-20 text-right shrink-0">
            {fmt(b.value)}
          </span>
        </div>
      ))}
    </div>
  )
}

export default function ProfitabilityCalc() {
  const [crop, setCrop] = useState('paddy')
  const [area, setArea] = useState(2)

  const cd = CROP_DATA[crop]
  const [marketPrice, setMarketPrice] = useState(cd.msp)

  const handleCropChange = (c) => {
    setCrop(c)
    setMarketPrice(CROP_DATA[c].msp)
  }

  const totalCost = cd.fertCost + cd.laborCost + cd.harvestCost

  const base = useMemo(() => {
    const rev = calcRevenue(cd.baseYield, marketPrice) * area
    const cost = totalCost * area
    const profit = rev - cost
    const roi = cost > 0 ? (profit / cost) * 100 : 0
    return { rev, cost, profit, roi }
  }, [crop, area, marketPrice])

  const opt = useMemo(() => {
    const rev = calcRevenue(cd.optYield, marketPrice) * area
    const cost = totalCost * area
    const profit = rev - cost
    const roi = cost > 0 ? (profit / cost) * 100 : 0
    return { rev, cost, profit, roi }
  }, [crop, area, marketPrice])

  const breakeven = totalCost / (0.405 * 10 * marketPrice)
  const breakevenPct = cd.optYield > 0 ? ((cd.optYield - breakeven) / breakeven) * 100 : 0

  return (
    <div className="flex flex-col gap-6">
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="text-sm font-semibold text-earth-900">Profitability & ROI Calculator</h2>
            <p className="text-[10px] text-earth-400 mt-0.5">లాభదాయకత అంచనా · Per-acre estimates</p>
          </div>
        </div>

        <div className="p-5 flex flex-col gap-6">
          <div className="flex flex-col gap-4">
            <div>
              <p className="section-title mb-2">Crop</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(CROP_DATA).map(([k, v]) => (
                  <button
                    key={k}
                    onClick={() => handleCropChange(k)}
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold transition-all ${
                      crop === k
                        ? 'bg-forest-900 text-white shadow-sm'
                        : 'bg-earth-100 text-earth-600 hover:bg-earth-200'
                    }`}
                  >
                    {v.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
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
              <div>
                <label className="section-title block mb-1.5">
                  Market Price (₹/quintal)
                  <span className="ml-1 normal-case text-earth-400 font-normal tracking-normal">MSP: ₹{cd.msp}</span>
                </label>
                <input
                  type="number"
                  min={100}
                  step={10}
                  value={marketPrice}
                  onChange={e => setMarketPrice(Math.max(100, parseFloat(e.target.value) || 100))}
                  className="field-input"
                />
              </div>
            </div>
          </div>

          <div>
            <p className="section-title mb-3">Base vs Optimized (per acre · total {area} acres)</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-forest-100 rounded-2xl p-4 border border-forest-300">
                <p className="text-[10px] font-semibold text-forest-600 uppercase tracking-wider mb-1">Revenue</p>
                <p className="font-display text-2xl font-semibold text-forest-900 tabular-nums">{fmt(opt.rev)}</p>
                <p className="text-[10px] text-forest-700 mt-1">Base: {fmt(base.rev)}</p>
              </div>

              <div className="bg-amber-100 rounded-2xl p-4 border border-amber-500/30">
                <p className="text-[10px] font-semibold text-amber-700 uppercase tracking-wider mb-1">Total Cost</p>
                <p className="font-display text-2xl font-semibold text-earth-900 tabular-nums">{fmt(opt.cost)}</p>
                <p className="text-[10px] text-amber-700 mt-1">Same base & opt.</p>
              </div>

              <div className={`rounded-2xl p-4 border ${opt.profit >= 0 ? 'bg-forest-100 border-forest-300' : 'bg-crimson-100 border-crimson-200'}`}>
                <p className={`text-[10px] font-semibold uppercase tracking-wider mb-1 ${opt.profit >= 0 ? 'text-forest-600' : 'text-crimson-600'}`}>
                  Net Profit
                </p>
                <p className={`font-display text-2xl font-semibold tabular-nums ${opt.profit >= 0 ? 'text-forest-900' : 'text-crimson-700'}`}>
                  {fmt(opt.profit)}
                </p>
                <p className={`text-[10px] mt-1 ${opt.profit >= 0 ? 'text-forest-700' : 'text-crimson-600'}`}>
                  Base: {fmt(base.profit)}
                </p>
              </div>

              <div className="bg-forest-100 rounded-2xl p-4 border border-forest-300">
                <p className="text-[10px] font-semibold text-forest-600 uppercase tracking-wider mb-1">ROI</p>
                <p className="font-display text-2xl font-semibold text-forest-900 tabular-nums">
                  {opt.roi.toFixed(1)}%
                </p>
                <p className="text-[10px] text-forest-700 mt-1">Base: {base.roi.toFixed(1)}%</p>
              </div>
            </div>
          </div>

          <div className="bg-earth-50 border border-earth-200 rounded-2xl p-4">
            <p className="section-title mb-1">Break-even Analysis</p>
            <p className="text-sm text-earth-900 mt-1">
              You need{' '}
              <span className="font-semibold text-crimson-700">{breakeven.toFixed(2)} t/ha</span>
              {' '}to break even. Your expected yield is{' '}
              <span className="font-semibold text-forest-800">{cd.optYield} t/ha</span>
              {' '}—{' '}
              <span className="font-semibold text-forest-700">{breakevenPct.toFixed(1)}% above break-even.</span>
            </p>
          </div>

          <div>
            <p className="section-title mb-3">Revenue vs Cost Comparison</p>
            <BarComparison
              baseRev={base.rev}
              baseCost={base.cost}
              optRev={opt.rev}
              optCost={opt.cost}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
