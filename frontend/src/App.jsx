import { useState } from 'react'
import Navbar from './components/Navbar'
import AdminDashboard from './components/admin/AdminDashboard'
import OfficialsDashboard from './components/officials/OfficialsDashboard'
import FarmerPortal from './components/farmer/FarmerPortal'

const TABS = [
  {
    id: 'admin',
    label: 'State Admin',
    sub: 'Commissioner View',
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm0 4l5 2.18V11c0 3.5-2.33 6.79-5 7.93-2.67-1.14-5-4.43-5-7.93V7.18L12 5z"/>
      </svg>
    ),
  },
  {
    id: 'officials',
    label: 'District Dashboard',
    sub: 'JDA / DDA View',
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/>
      </svg>
    ),
  },
  {
    id: 'farmer',
    label: 'Farmer Portal',
    sub: 'రైతు పోర్టల్',
    icon: (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M17 8C8 10 5.9 16.17 3.82 21.34L5.71 22l1-2.3A4.49 4.49 0 0 0 8 20C19 20 22 3 22 3c-1 2-8 2-8 2 0-2 3-3 3-3-4.5 1.5-6 4-6 4C10 8 8 9 8 9c1-3 3-4 3-4-5 2-7 9-7 9s1-8 10-9c0 0 7-3 8 5z"/>
      </svg>
    ),
  },
]

export default function App() {
  const [tab, setTab] = useState('admin')

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* Tab strip */}
      <div className="bg-earth-50/80 backdrop-blur-sm border-b border-earth-200 sticky top-0 z-40">
        <div className="max-w-screen-2xl mx-auto px-6">
          <div className="flex gap-1 py-2">
            {TABS.map(t => {
              const active = tab === t.id
              return (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 relative
                    ${active
                      ? 'bg-forest-900 text-white shadow-sm'
                      : 'text-earth-600 hover:text-earth-900 hover:bg-earth-100'
                    }`}
                >
                  <span className={active ? 'opacity-90' : 'opacity-60'}>{t.icon}</span>
                  <span>{t.label}</span>
                  {t.sub && (
                    <span className={`text-xs ${active ? 'text-forest-300' : 'text-earth-400'}`}>
                      {t.sub}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      <main className="flex-1 max-w-screen-2xl mx-auto w-full px-6 py-6">
        {tab === 'admin'     && <AdminDashboard />}
        {tab === 'officials' && <OfficialsDashboard />}
        {tab === 'farmer'    && <FarmerPortal />}
      </main>
    </div>
  )
}
