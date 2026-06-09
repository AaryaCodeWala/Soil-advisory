import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, Legend, LineChart, Line, CartesianGrid,
} from 'recharts'

const DISTRICTS = [
  { id: 'krishna',       name: 'Krishna',       region: 'Coastal',     status: 'complete', farmers: 47832, area: 8727,  avgPH: 6.8,  avgOC: 0.45, nDef: 68, pDef: 45, kDef: 22, score: 72, maos: 12, vaas: 84,  lastUpdate: 'Jun 1'  },
  { id: 'guntur',        name: 'Guntur',         region: 'Coastal',     status: 'complete', farmers: 52100, area: 11391, avgPH: 7.1,  avgOC: 0.52, nDef: 72, pDef: 51, kDef: 18, score: 68, maos: 14, vaas: 97,  lastUpdate: 'May 28' },
  { id: 'west_godavari', name: 'West Godavari',  region: 'Godavari',    status: 'complete', farmers: 38900, area: 7742,  avgPH: 6.6,  avgOC: 0.61, nDef: 59, pDef: 38, kDef: 14, score: 78, maos: 10, vaas: 72,  lastUpdate: 'May 20' },
  { id: 'east_godavari', name: 'East Godavari',  region: 'Godavari',    status: 'partial',  farmers: 21400, area: 10807, avgPH: 6.9,  avgOC: 0.48, nDef: 63, pDef: 42, kDef: 19, score: 71, maos: 13, vaas: 91,  lastUpdate: 'Apr 15' },
  { id: 'kurnool',       name: 'Kurnool',        region: 'Rayalaseema', status: 'partial',  farmers: 12800, area: 17658, avgPH: 7.4,  avgOC: 0.38, nDef: 78, pDef: 55, kDef: 28, score: 61, maos: 11, vaas: 78,  lastUpdate: 'Apr 2'  },
  { id: 'nellore',       name: 'Nellore',        region: 'Coastal',     status: 'pending',  farmers: 0,     area: 13076, avgPH: null, avgOC: null, nDef: null, pDef: null, kDef: null, score: null, maos: 9, vaas: 65,  lastUpdate: null     },
  { id: 'prakasam',      name: 'Prakasam',       region: 'Coastal',     status: 'pending',  farmers: 0,     area: 17626, avgPH: null, avgOC: null, nDef: null, pDef: null, kDef: null, score: null, maos: 12, vaas: 83,  lastUpdate: null     },
  { id: 'kadapa',        name: 'YSR Kadapa',     region: 'Rayalaseema', status: 'pending',  farmers: 0,     area: 15359, avgPH: null, avgOC: null, nDef: null, pDef: null, kDef: null, score: null, maos: 8,  vaas: 58,  lastUpdate: null     },
  { id: 'anantapur',     name: 'Anantapur',      region: 'Rayalaseema', status: 'pending',  farmers: 0,     area: 19130, avgPH: null, avgOC: null, nDef: null, pDef: null, kDef: null, score: null, maos: 14, vaas: 96,  lastUpdate: null     },
  { id: 'chittoor',      name: 'Chittoor',       region: 'Rayalaseema', status: 'pending',  farmers: 0,     area: 15152, avgPH: null, avgOC: null, nDef: null, pDef: null, kDef: null, score: null, maos: 10, vaas: 70,  lastUpdate: null     },
  { id: 'visakhapatnam', name: 'Visakhapatnam',  region: 'Northern',    status: 'pending',  farmers: 0,     area: 11161, avgPH: null, avgOC: null, nDef: null, pDef: null, kDef: null, score: null, maos: 11, vaas: 77,  lastUpdate: null     },
  { id: 'vizianagaram',  name: 'Vizianagaram',   region: 'Northern',    status: 'pending',  farmers: 0,     area: 6539,  avgPH: null, avgOC: null, nDef: null, pDef: null, kDef: null, score: null, maos: 7,  vaas: 52,  lastUpdate: null     },
  { id: 'srikakulam',    name: 'Srikakulam',     region: 'Northern',    status: 'pending',  farmers: 0,     area: 5837,  avgPH: null, avgOC: null, nDef: null, pDef: null, kDef: null, score: null, maos: 8,  vaas: 55,  lastUpdate: null     },
]

const ALERTS = [
  { id: 1, level: 'critical', district: 'Kurnool',       msg: 'Avg N deficiency 78% — highest in mapped districts. Immediate fertilizer advisory push recommended.', time: '2h ago' },
  { id: 2, level: 'critical', district: 'Guntur',        msg: '72% area N-deficient. Pre-season Urea distribution insufficient for projected Kharif demand.', time: '5h ago' },
  { id: 3, level: 'warning',  district: 'East Godavari', msg: 'Only 50% mandals covered in partial mapping. 3 mandals have no SHC data since 2023.', time: '1d ago' },
  { id: 4, level: 'warning',  district: 'Nellore',       msg: 'District mapping not started. Kharif sowing window opens June 15 — data urgently needed.', time: '2d ago' },
  { id: 5, level: 'info',     district: 'West Godavari', msg: 'Mapping complete. OC at 0.61% — highest in region. Recommend as model district for organic push.', time: '3d ago' },
]

const ACTIVITY = [
  { time: '10:42', actor: 'MAO Vijayawada-2', action: 'Uploaded 47 SHC records for Nandigama mandal, Krishna', type: 'upload' },
  { time: '09:18', actor: 'VAA Gudivada',     action: 'Completed field visit — 12 farmers advised, Fertilizer plan distributed', type: 'field' },
  { time: '08:55', actor: 'JDA Krishna',      action: 'Generated pH deficiency report for Q2 2026 — 68% area below 6.5', type: 'report' },
  { time: 'Yesterday', actor: 'State Server', action: 'Sentinel-2 composite refreshed for post-Kharif 2025 window', type: 'system' },
  { time: 'Yesterday', actor: 'MAO Tenali',   action: 'Submitted 83 soil samples for Guntur batch processing', type: 'upload' },
]

const ROLLOUT_TREND = [
  { month: 'Jan', farmers: 12000, districts: 1 },
  { month: 'Feb', farmers: 24000, districts: 2 },
  { month: 'Mar', farmers: 48000, districts: 3 },
  { month: 'Apr', farmers: 86000, districts: 4 },
  { month: 'May', farmers: 120000, districts: 5 },
  { month: 'Jun', farmers: 173032, districts: 5 },
]

const STATUS_META = {
  complete: { label: 'Complete',     bg: 'bg-forest-100', text: 'text-forest-700', dot: 'bg-forest-500', tile: '#1B4332' },
  partial:  { label: 'In Progress',  bg: 'bg-amber-100',  text: 'text-amber-700',  dot: 'bg-amber-500',  tile: '#C4622D' },
  pending:  { label: 'Not Started',  bg: 'bg-earth-100',  text: 'text-earth-500',  dot: 'bg-earth-300',  tile: '#C8BFB5' },
}

const REGION_DISTRICTS = {
  'Northern':    ['Srikakulam', 'Vizianagaram', 'Visakhapatnam'],
  'Godavari':    ['East Godavari', 'West Godavari'],
  'Coastal':     ['Krishna', 'Guntur', 'Nellore', 'Prakasam'],
  'Rayalaseema': ['Kurnool', 'YSR Kadapa', 'Anantapur', 'Chittoor'],
}

const totalFarmers   = DISTRICTS.reduce((a, d) => a + d.farmers, 0)
const mappedDistricts = DISTRICTS.filter(d => d.status !== 'pending').length
const completeDistricts = DISTRICTS.filter(d => d.status === 'complete').length
const avgScore       = Math.round(DISTRICTS.filter(d => d.score).reduce((a, d) => a + d.score, 0) / DISTRICTS.filter(d => d.score).length)
const fertSavingsCr  = ((totalFarmers * 2.4) / 1e7).toFixed(1)
const defChart = DISTRICTS.filter(d => d.status !== 'pending').map(d => ({
  name: d.name.split(' ')[0],
  N: d.nDef, P: d.pDef, K: d.kDef,
}))

function ScoreBadge({ score }) {
  if (score === null) return <span className="text-earth-300 text-xs">—</span>
  const color = score >= 75 ? 'text-forest-600' : score >= 60 ? 'text-amber-600' : 'text-crimson-600'
  return <span className={`font-display text-base font-semibold ${color}`}>{score}</span>
}

function DefBar({ value, max = 100 }) {
  if (value === null) return <span className="text-earth-300 text-xs">—</span>
  const color = value > 65 ? 'bg-crimson-500' : value > 40 ? 'bg-amber-500' : 'bg-forest-500'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-earth-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-xs tabular-nums text-earth-700">{value}%</span>
    </div>
  )
}

function KPICard({ label, value, sub, icon, accent = 'forest', trend }) {
  return (
    <div className="card px-5 py-4 flex flex-col gap-1">
      <div className="flex items-center justify-between mb-1">
        <span className="section-title">{label}</span>
        <span className="text-lg">{icon}</span>
      </div>
      <span className={`font-display text-2xl font-semibold text-${accent}-800 leading-none`}>{value}</span>
      {sub && <span className="text-[11px] text-earth-400 mt-0.5">{sub}</span>}
      {trend && (
        <span className="text-[10px] font-medium text-forest-600 mt-0.5">↑ {trend}</span>
      )}
    </div>
  )
}

function APSchematic() {
  const byName = Object.fromEntries(DISTRICTS.map(d => [d.name, d]))
  return (
    <div className="card p-4">
      <p className="section-title mb-3">District Mapping Status</p>
      <div className="flex flex-col gap-2">
        {Object.entries(REGION_DISTRICTS).map(([region, names]) => (
          <div key={region}>
            <p className="text-[9px] text-earth-400 uppercase tracking-widest mb-1">{region}</p>
            <div className="flex flex-wrap gap-1.5">
              {names.map(name => {
                const d = byName[name]
                const meta = STATUS_META[d?.status || 'pending']
                return (
                  <div
                    key={name}
                    className={`rounded-lg px-2.5 py-1.5 text-[10px] font-semibold ${meta.bg} ${meta.text} flex items-center gap-1.5`}
                    title={d?.status}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${meta.dot} flex-shrink-0`} />
                    {name.replace('YSR ', '').replace('West ', 'W.').replace('East ', 'E.').replace('Visakhapatnam', 'Vizag')}
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-3 mt-3 pt-3 border-t border-earth-100">
        {Object.entries(STATUS_META).map(([k, v]) => (
          <div key={k} className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${v.dot}`} />
            <span className="text-[9px] text-earth-500">{v.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

const DefTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-earth-200 rounded-xl shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-earth-800 mb-1">{label} District</p>
      {payload.map(p => (
        <div key={p.name} className="flex items-center gap-2">
          <span style={{ color: p.fill }} className="font-bold">{p.name}</span>
          <span className="text-earth-700">{p.value}% deficient</span>
        </div>
      ))}
    </div>
  )
}

const TrendTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-earth-200 rounded-xl shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-earth-600 mb-1">{label} 2026</p>
      <p className="text-earth-900">{payload[0]?.value?.toLocaleString()} farmers</p>
    </div>
  )
}

function AlertPanel() {
  const levelMeta = {
    critical: { bg: 'bg-crimson-50', border: 'border-crimson-200', dot: 'bg-crimson-500', text: 'text-crimson-700', label: 'CRITICAL' },
    warning:  { bg: 'bg-amber-50',   border: 'border-amber-200',   dot: 'bg-amber-500',   text: 'text-amber-700',  label: 'WARNING'  },
    info:     { bg: 'bg-forest-50',  border: 'border-forest-200',  dot: 'bg-forest-400',  text: 'text-forest-700', label: 'INFO'     },
  }
  return (
    <div className="card flex flex-col">
      <div className="card-header justify-between">
        <h2 className="text-sm font-semibold text-earth-900">Intervention Alerts</h2>
        <span className="text-[10px] bg-crimson-100 text-crimson-700 font-bold px-2 py-0.5 rounded-full">
          2 Critical
        </span>
      </div>
      <div className="flex flex-col divide-y divide-earth-50 flex-1">
        {ALERTS.map(a => {
          const m = levelMeta[a.level]
          return (
            <div key={a.id} className={`px-4 py-3 ${a.level === 'critical' ? 'bg-crimson-50/50' : ''}`}>
              <div className="flex items-start gap-3">
                <span className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${m.dot}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={`text-[9px] font-bold tracking-wider ${m.text}`}>{m.label}</span>
                    <span className="text-xs font-semibold text-earth-800">{a.district}</span>
                    <span className="text-[9px] text-earth-400 ml-auto">{a.time}</span>
                  </div>
                  <p className="text-[11px] text-earth-600 leading-relaxed">{a.msg}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ActivityFeed() {
  const typeMeta = {
    upload: { icon: '↑', color: 'text-forest-600 bg-forest-100' },
    field:  { icon: '◎', color: 'text-amber-600 bg-amber-100'   },
    report: { icon: '≡', color: 'text-earth-600 bg-earth-100'   },
    system: { icon: '⚙', color: 'text-earth-500 bg-earth-50'    },
  }
  return (
    <div className="card flex flex-col">
      <div className="card-header">
        <h2 className="text-sm font-semibold text-earth-900">Field Activity Log</h2>
      </div>
      <div className="flex flex-col divide-y divide-earth-50">
        {ACTIVITY.map((a, i) => {
          const m = typeMeta[a.type]
          return (
            <div key={i} className="px-4 py-3 flex items-start gap-3">
              <span className={`w-6 h-6 rounded-lg flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${m.color}`}>
                {m.icon}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11px] font-semibold text-earth-700">{a.actor}</span>
                  <span className="text-[9px] text-earth-400 tabular-nums flex-shrink-0">{a.time}</span>
                </div>
                <p className="text-[11px] text-earth-500 leading-snug mt-0.5">{a.action}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function AdminDashboard() {
  const [sortCol, setSortCol]   = useState('status')
  const [viewDistrict, setView] = useState(null)

  const sorted = [...DISTRICTS].sort((a, b) => {
    if (sortCol === 'score') return (b.score ?? -1) - (a.score ?? -1)
    if (sortCol === 'farmers') return b.farmers - a.farmers
    if (sortCol === 'nDef') return (b.nDef ?? -1) - (a.nDef ?? -1)
    const order = { complete: 0, partial: 1, pending: 2 }
    return order[a.status] - order[b.status]
  })

  const ThButton = ({ col, children }) => (
    <th
      onClick={() => setSortCol(col)}
      className={`px-3 py-2 text-left section-title cursor-pointer select-none hover:text-earth-700 transition-colors ${sortCol === col ? 'text-forest-700' : ''}`}
    >
      {children} {sortCol === col && '↓'}
    </th>
  )

  return (
    <div className="flex flex-col gap-5">

      {/* ── Admin identity banner ── */}
      <div className="bg-forest-900 rounded-2xl px-6 py-4 flex items-center justify-between text-white overflow-hidden relative">
        <div
          className="absolute inset-0 opacity-[0.05]"
          style={{ backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,0.5) 10px, rgba(255,255,255,0.5) 11px)' }}
        />
        <div className="relative">
          <div className="flex items-center gap-3 mb-1">
            <span className="text-[9px] font-bold tracking-widest bg-amber-400 text-amber-900 px-2 py-0.5 rounded-full uppercase">
              State Level · Admin View
            </span>
            <span className="text-[10px] text-forest-400">Access: All Districts · Read/Write</span>
          </div>
          <h1 className="font-display text-xl font-semibold leading-tight">
            Commissioner of Agriculture, Govt. of Andhra Pradesh
          </h1>
          <p className="text-[11px] text-forest-400 mt-0.5">
            AI-Enabled Soil Health Intelligence — State Command Center · Krishna Pilot → AP Rollout
          </p>
        </div>
        <div className="relative flex items-center gap-6 text-[11px] text-forest-300">
          <div className="text-right">
            <p className="font-semibold text-white font-display text-base">{DISTRICTS.length}</p>
            <p>Districts total</p>
          </div>
          <div className="w-px h-8 bg-forest-700" />
          <div className="text-right">
            <p className="font-semibold text-white font-display text-base">{completeDistricts + '/' + DISTRICTS.length}</p>
            <p>Fully mapped</p>
          </div>
          <div className="w-px h-8 bg-forest-700" />
          <div className="text-right">
            <div className="flex items-center gap-1.5 justify-end">
              <span className="w-1.5 h-1.5 rounded-full bg-forest-400 animate-pulse" />
              <p className="font-semibold text-forest-300">Live</p>
            </div>
            <p>Updated hourly</p>
          </div>
        </div>
      </div>

      {/* ── State KPIs ── */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <KPICard label="Districts Mapped"    value={`${mappedDistricts}/${DISTRICTS.length}`} sub="3 complete, 2 partial"   icon="🗺" accent="forest" trend="+2 this month" />
        <KPICard label="Farmers Covered"     value={totalFarmers.toLocaleString()}            sub="across 5 districts"       icon="👨‍🌾" accent="forest" trend="+12,400 this month" />
        <KPICard label="Avg Soil Score"      value={`${avgScore}/100`}                        sub="mapped districts"         icon="🌱" accent="forest" />
        <KPICard label="Fertilizer Savings"  value={`₹${fertSavingsCr} Cr`}                  sub="vs blanket application"   icon="💰" accent="earth" trend="est. annualised" />
        <KPICard label="SHC Cards Issued"    value="1,24,567"                                 sub="state-wide 2025–26"       icon="📋" accent="earth" />
        <KPICard label="Critical Alerts"     value="2"                                        sub="N deficiency — urgent"    icon="⚠" accent="crimson" />
      </div>

      {/* ── District table + schematic ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">

        {/* Table */}
        <div className="lg:col-span-3 card overflow-hidden">
          <div className="card-header justify-between">
            <h2 className="text-sm font-semibold text-earth-900">District Status — All AP</h2>
            <span className="text-[10px] text-earth-400">Click column to sort</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-earth-50 border-b border-earth-100">
                <tr>
                  <ThButton col="status">District</ThButton>
                  <ThButton col="score">Score</ThButton>
                  <ThButton col="farmers">Farmers</ThButton>
                  <ThButton col="nDef">N Def</ThButton>
                  <th className="px-3 py-2 text-left section-title">P Def</th>
                  <th className="px-3 py-2 text-left section-title">Last Update</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-earth-50">
                {sorted.map(d => {
                  const m = STATUS_META[d.status]
                  return (
                    <tr
                      key={d.id}
                      className="hover:bg-earth-50/60 transition-colors cursor-pointer"
                      onClick={() => setView(d.id === viewDistrict ? null : d.id)}
                    >
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${m.dot}`} />
                          <span className="font-semibold text-earth-800">{d.name}</span>
                          <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded-full ${m.bg} ${m.text}`}>
                            {m.label}
                          </span>
                        </div>
                        <p className="text-[9px] text-earth-400 ml-4">{d.region} · {d.maos} MAOs · {d.vaas} VAAs</p>
                      </td>
                      <td className="px-3 py-2.5"><ScoreBadge score={d.score} /></td>
                      <td className="px-3 py-2.5 tabular-nums text-earth-700">{d.farmers > 0 ? d.farmers.toLocaleString() : <span className="text-earth-300">—</span>}</td>
                      <td className="px-3 py-2.5"><DefBar value={d.nDef} /></td>
                      <td className="px-3 py-2.5"><DefBar value={d.pDef} /></td>
                      <td className="px-3 py-2.5 text-earth-400">{d.lastUpdate ?? <span className="text-earth-200">—</span>}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right column: schematic + rollout */}
        <div className="lg:col-span-2 flex flex-col gap-5">
          <APSchematic />

          {/* Rollout trend */}
          <div className="card p-4">
            <p className="section-title mb-1">Farmer Coverage Rollout 2026</p>
            <p className="text-[11px] text-earth-400 mb-3">Cumulative farmers reached</p>
            <ResponsiveContainer width="100%" height={110}>
              <LineChart data={ROLLOUT_TREND} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#EDE8E0" />
                <XAxis dataKey="month" tick={{ fontSize: 9, fill: '#9E9590' }} />
                <YAxis tick={{ fontSize: 9, fill: '#9E9590' }} tickFormatter={v => v >= 1000 ? `${v/1000}k` : v} />
                <Tooltip content={<TrendTooltip />} />
                <Line type="monotone" dataKey="farmers" stroke="#1B4332" strokeWidth={2} dot={{ r: 3, fill: '#1B4332' }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Multi-district deficiency comparison ── */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-earth-900 mb-1">N / P / K Deficiency by District</h2>
        <p className="text-xs text-earth-400 mb-4">% of mapped area below ICAR critical threshold · mapped districts only</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={defChart} margin={{ top: 4, right: 8, left: -16, bottom: 0 }} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke="#EDE8E0" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#6B6560' }} />
            <YAxis tick={{ fontSize: 9, fill: '#9E9590' }} unit="%" domain={[0, 100]} />
            <Tooltip content={<DefTooltip />} />
            <Legend wrapperStyle={{ fontSize: 10, paddingTop: 8 }} />
            <Bar dataKey="N" name="Nitrogen" fill="#9B2335" radius={[3, 3, 0, 0]} />
            <Bar dataKey="P" name="Phosphorus" fill="#C4622D" radius={[3, 3, 0, 0]} />
            <Bar dataKey="K" name="Potassium" fill="#1B4332" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* ── Alerts + Activity ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <AlertPanel />
        <ActivityFeed />
      </div>

      {/* ── Budget impact ── */}
      <div className="card p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-earth-900">Budget & Fertilizer Subsidy Impact</h2>
            <p className="text-xs text-earth-400">Estimated savings from precision vs blanket application</p>
          </div>
          <span className="text-[10px] text-earth-400 bg-earth-100 px-2 py-1 rounded-lg">Projected FY 2026–27</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Urea Saved',       value: '4,820 MT',  sub: 'across mapped districts',       color: 'text-forest-700' },
            { label: 'DAP Optimised',    value: '1,240 MT',  sub: '18% reduction vs baseline',     color: 'text-forest-700' },
            { label: 'Subsidy Saving',   value: '₹2.3 Cr',   sub: 'direct input cost reduction',   color: 'text-forest-700' },
            { label: 'Projected for AP', value: '₹18.6 Cr',  sub: 'all 13 districts at full scale', color: 'text-amber-700' },
          ].map(item => (
            <div key={item.label} className="bg-earth-50 rounded-xl p-4">
              <p className="section-title mb-1.5">{item.label}</p>
              <p className={`font-display text-xl font-semibold ${item.color}`}>{item.value}</p>
              <p className="text-[10px] text-earth-400 mt-0.5">{item.sub}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-earth-100 text-[11px] text-earth-500">
          Methodology: Precision N dose per SHC recommendation vs 120 kg/ha blanket Urea. Urea cost ₹266.50/50kg bag.
          Savings scaled to actual farm area from APSAC records.
        </div>
      </div>

    </div>
  )
}
