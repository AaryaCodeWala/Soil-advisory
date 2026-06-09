import { useState } from 'react'
import FarmerAdvisory from './FarmerAdvisory'
import ProfitabilityCalc from './ProfitabilityCalc'
import PestAlert from './PestAlert'
import YieldPredict from './YieldPredict'
import IrrigationScheduler from './IrrigationScheduler'
import GovSchemes from './GovSchemes'
import CropCalendar from './CropCalendar'
import CarbonCredits from './CarbonCredits'

const SUB_TABS = [
  { id: 'advisory',   label: 'Fertilizer Advisory', te: 'ఎరువుల సలహా',     icon: '🌱' },
  { id: 'profit',     label: 'Profitability',        te: 'లాభదాయకత',         icon: '₹'  },
  { id: 'pest',       label: 'Pest Alerts',          te: 'తెగుళ్ళ హెచ్చరిక',  icon: '⚠'  },
  { id: 'yield',      label: 'Yield Forecast',       te: 'దిగుబడి అంచనా',    icon: '📈' },
  { id: 'irrigation', label: 'Irrigation',           te: 'నీటిపారుదల',       icon: '💧' },
  { id: 'schemes',    label: 'Gov Schemes',          te: 'ప్రభుత్వ పథకాలు',   icon: '🏛' },
  { id: 'calendar',   label: 'Crop Calendar',        te: 'పంట క్యాలెండర్',    icon: '📅' },
  { id: 'carbon',     label: 'Carbon Credits',       te: 'కార్బన్ క్రెడిట్స్', icon: '🌿' },
]

function TabContent({ activeTab }) {
  switch (activeTab) {
    case 'advisory':   return <FarmerAdvisory />
    case 'profit':     return <ProfitabilityCalc />
    case 'pest':       return <PestAlert />
    case 'yield':      return <YieldPredict />
    case 'irrigation': return <IrrigationScheduler />
    case 'schemes':    return <GovSchemes />
    case 'calendar':   return <CropCalendar />
    case 'carbon':     return <CarbonCredits />
    default:           return <FarmerAdvisory />
  }
}

export default function FarmerPortal() {
  const [activeTab, setActiveTab] = useState('advisory')

  return (
    <div className="flex flex-col gap-0">
      <div className="bg-white/50 backdrop-blur border-b border-earth-100 rounded-2xl px-3 py-2 mb-6 flex gap-1 overflow-x-auto">
        {SUB_TABS.map(tab => {
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex flex-col items-center gap-0.5 px-4 py-2.5 rounded-xl text-xs font-medium transition-all whitespace-nowrap min-w-fit relative ${
                isActive
                  ? 'bg-forest-900 text-white'
                  : 'text-earth-600 hover:bg-earth-100'
              }`}
            >
              <span className="text-base leading-none">{tab.icon}</span>
              <span className="font-semibold leading-tight">{tab.label}</span>
              <span className={`text-[9px] leading-none ${isActive ? 'opacity-70' : 'opacity-50'}`}>{tab.te}</span>
            </button>
          )
        })}
      </div>

      <TabContent activeTab={activeTab} />
    </div>
  )
}
