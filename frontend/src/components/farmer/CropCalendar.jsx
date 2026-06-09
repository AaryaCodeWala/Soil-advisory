import { useState } from 'react'

const CALENDAR = {
  paddy: {
    name: 'Paddy (వరి)', color: '#1B4332',
    operations: [
      { label: 'Land Prep', start: 5.5, end: 6.5, type: 'prep' },
      { label: 'Nursery', start: 6.0, end: 6.75, type: 'sow' },
      { label: 'Transplanting', start: 6.75, end: 7.5, type: 'sow' },
      { label: 'Basal Fertilizer', start: 6.75, end: 7.5, type: 'fertilizer' },
      { label: 'Top Dressing 1', start: 8.0, end: 8.5, type: 'fertilizer' },
      { label: 'Top Dressing 2', start: 9.5, end: 10.0, type: 'fertilizer' },
      { label: 'Irrigation', start: 7.0, end: 10.5, type: 'water' },
      { label: 'Harvest', start: 11.0, end: 12.0, type: 'harvest' },
    ],
  },
  cotton: {
    name: 'Cotton (పత్తి)', color: '#9B2335',
    operations: [
      { label: 'Land Prep', start: 5.0, end: 6.0, type: 'prep' },
      { label: 'Sowing', start: 6.0, end: 7.0, type: 'sow' },
      { label: 'Basal Fertilizer', start: 6.0, end: 7.0, type: 'fertilizer' },
      { label: 'Top Dressing', start: 8.0, end: 9.0, type: 'fertilizer' },
      { label: 'Irrigation', start: 6.0, end: 10.0, type: 'water' },
      { label: 'Picking 1', start: 10.5, end: 11.5, type: 'harvest' },
      { label: 'Picking 2', start: 12.0, end: 1.5, type: 'harvest' },
    ],
  },
  groundnut: {
    name: 'Groundnut (వేరుసెనగ)', color: '#D4A853',
    operations: [
      { label: 'Land Prep', start: 5.5, end: 6.5, type: 'prep' },
      { label: 'Sowing', start: 6.5, end: 7.5, type: 'sow' },
      { label: 'Basal Fertilizer', start: 6.5, end: 7.0, type: 'fertilizer' },
      { label: 'Gypsum Application', start: 8.0, end: 8.5, type: 'fertilizer' },
      { label: 'Irrigation', start: 7.0, end: 9.5, type: 'water' },
      { label: 'Harvest', start: 10.0, end: 11.0, type: 'harvest' },
    ],
  },
  red_gram: {
    name: 'Red Gram (కందులు)', color: '#6B4226',
    operations: [
      { label: 'Sowing', start: 6.0, end: 7.5, type: 'sow' },
      { label: 'Basal Fertilizer', start: 6.0, end: 6.5, type: 'fertilizer' },
      { label: 'Top Dressing', start: 9.0, end: 9.5, type: 'fertilizer' },
      { label: 'Harvest', start: 1.0, end: 2.0, type: 'harvest' },
    ],
  },
}

const TYPE_STYLES = {
  prep:       { bg: 'bg-amber-200',  label: 'Land Prep' },
  sow:        { bg: 'bg-green-600',  label: 'Sowing' },
  fertilizer: { bg: 'bg-amber-500',  label: 'Fertilizer' },
  water:      { bg: 'bg-blue-400',   label: 'Irrigation' },
  harvest:    { bg: 'bg-red-600',    label: 'Harvest' },
}

const KHARIF_MONTHS = [6, 7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5]
const MONTH_NAMES   = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function monthToKharif(m) {
  return ((m - 6 + 12) % 12)
}

function getBarStyle(start, end) {
  const startIdx = monthToKharif(Math.floor(start))
  const startFrac = start - Math.floor(start)
  const leftPct = ((startIdx + startFrac) / 12) * 100

  let wraps = end < start && end < 6
  let widthMonths

  if (wraps) {
    const beforeWrap = 13 - start
    const afterWrap = end - 1
    widthMonths = beforeWrap + afterWrap
  } else {
    widthMonths = end - start
  }

  const widthPct = (widthMonths / 12) * 100
  return { left: `${leftPct}%`, width: `${widthPct}%` }
}

export default function CropCalendar() {
  const [selectedCrop, setSelectedCrop] = useState('all')

  const today = new Date()
  const todayMonthNum = today.getMonth() + 1
  const todayKharif = monthToKharif(todayMonthNum)
  const todayFrac = today.getDate() / 31
  const todayPct = ((todayKharif + todayFrac) / 12) * 100

  const visibleCrops = selectedCrop === 'all'
    ? Object.keys(CALENDAR)
    : [selectedCrop]

  return (
    <div className="flex flex-col gap-6">
      <div className="card">
        <div className="card-header">
          <span className="text-base mr-2">📅</span>
          <span className="font-semibold text-earth-900">Crop Calendar — Krishna District</span>
          <span className="ml-2 text-[10px] text-earth-500">పంట క్యాలెండర్</span>
        </div>
        <div className="px-5 py-4 flex flex-col gap-5">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedCrop('all')}
              className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                selectedCrop === 'all'
                  ? 'bg-earth-800 text-white border-earth-800'
                  : 'bg-white text-earth-600 border-earth-200 hover:border-earth-500'
              }`}
            >
              All Crops
            </button>
            {Object.entries(CALENDAR).map(([key, val]) => (
              <button
                key={key}
                onClick={() => setSelectedCrop(selectedCrop === key ? 'all' : key)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                  selectedCrop === key
                    ? 'text-white border-transparent'
                    : 'bg-white text-earth-600 border-earth-200 hover:border-earth-400'
                }`}
                style={selectedCrop === key ? { backgroundColor: val.color, borderColor: val.color } : {}}
              >
                {val.name.split(' ')[0]}
              </button>
            ))}
          </div>

          <div className="overflow-x-auto">
            <div style={{ minWidth: 640 }}>
              <div className="flex">
                <div style={{ width: 120, minWidth: 120 }} />
                <div className="flex flex-1">
                  {KHARIF_MONTHS.map((m, i) => (
                    <div key={i} className="flex-1 text-center text-[10px] font-semibold text-earth-500 pb-2 border-b border-earth-100">
                      {MONTH_NAMES[m - 1]}
                    </div>
                  ))}
                </div>
              </div>

              <div className="relative">
                <div
                  className="absolute top-0 bottom-0 w-px bg-red-500 z-10"
                  style={{ left: `calc(120px + ${todayPct}% * (100% - 120px) / 100)` }}
                >
                  <div className="absolute -top-1 left-1 bg-red-500 text-white text-[8px] font-bold px-1 py-0.5 rounded whitespace-nowrap">
                    Today
                  </div>
                </div>

                {visibleCrops.map(cropKey => {
                  const crop = CALENDAR[cropKey]
                  return (
                    <div key={cropKey} className="flex items-center border-b border-earth-50 last:border-0 py-2 min-h-[48px]">
                      <div
                        className="text-[10px] font-semibold pr-3 shrink-0 text-right leading-tight"
                        style={{ width: 120, minWidth: 120, color: crop.color }}
                      >
                        {crop.name.split('(')[0].trim()}
                        <br />
                        <span className="font-normal text-earth-400">
                          {crop.name.match(/\(([^)]+)\)/)?.[1] ?? ''}
                        </span>
                      </div>
                      <div className="flex-1 relative" style={{ height: 32 }}>
                        {crop.operations.map((op, i) => {
                          const style = getBarStyle(op.start, op.end)
                          const widthNum = parseFloat(style.width)
                          const typeStyle = TYPE_STYLES[op.type]
                          return (
                            <div
                              key={i}
                              className={`absolute top-1 bottom-1 rounded-md ${typeStyle.bg} flex items-center justify-center overflow-hidden`}
                              style={{ left: style.left, width: style.width, opacity: 0.85 }}
                              title={op.label}
                            >
                              {widthNum > 8 && (
                                <span className="text-[8px] font-semibold text-white px-1 truncate leading-none">
                                  {op.label}
                                </span>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            {Object.entries(TYPE_STYLES).map(([key, val]) => (
              <div key={key} className="flex items-center gap-1.5">
                <div className={`w-3 h-3 rounded-sm ${val.bg}`} />
                <span className="text-[10px] text-earth-600 font-medium">{val.label}</span>
              </div>
            ))}
            <div className="flex items-center gap-1.5">
              <div className="w-px h-3 bg-red-500" />
              <span className="text-[10px] text-earth-600 font-medium">Today</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
