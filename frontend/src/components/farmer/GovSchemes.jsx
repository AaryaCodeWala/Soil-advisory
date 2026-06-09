import { useState } from 'react'

const SCHEMES = [
  {
    id: 'pmkisan',
    name: 'PM-KISAN',
    te: 'పిఎం కిసాన్',
    benefit: '₹6,000/year',
    description: 'Direct income support in 3 equal instalments of ₹2,000 to eligible farmer families.',
    eligibility: ['Any land holding size', 'Must have Aadhaar', 'Must have land records'],
    crops: ['paddy','cotton','groundnut','red_gram'],
    minAcres: 0, maxAcres: 999,
    category: 'income',
    apply: 'pmkisan.gov.in / Nearest CSC',
    color: 'forest',
  },
  {
    id: 'rythu_bharosa',
    name: 'AP Rythu Bharosa',
    te: 'రైతు భరోసా',
    benefit: '₹13,500/year',
    description: 'AP state scheme providing ₹7,500 for input costs + ₹6,000 PM-KISAN to AP farmers.',
    eligibility: ['AP domicile', 'Land owner or tenant farmer', 'Aadhaar linked'],
    crops: ['paddy','cotton','groundnut','red_gram'],
    minAcres: 0, maxAcres: 999,
    category: 'income',
    apply: 'ap.gov.in/rythu-bharosa',
    color: 'forest',
  },
  {
    id: 'pmfby',
    name: 'PM Fasal Bima Yojana',
    te: 'పంట బీమా',
    benefit: 'Crop insurance (sum insured up to ₹50,000/ha)',
    description: 'Crop insurance covering losses from natural calamities, pests, diseases. Premium: 1.5-2% for Kharif.',
    eligibility: ['Any farmer with land records', 'Enrol before sowing season', 'Aadhaar + bank account'],
    crops: ['paddy','cotton','groundnut','red_gram'],
    minAcres: 0, maxAcres: 999,
    category: 'insurance',
    apply: 'pmfby.gov.in / Bank branch',
    color: 'amber',
  },
  {
    id: 'drip',
    name: 'PM Krishi Sinchai Yojana',
    te: 'డ్రిప్ సబ్సిడీ',
    benefit: '55% subsidy on drip/sprinkler cost',
    description: 'Subsidy on micro-irrigation systems (drip & sprinkler). Small farmers get 55%, others 45%.',
    eligibility: ['Small/marginal farmers (<2 ha) get 55%', 'Others get 45%', 'AP MIDH registration required'],
    crops: ['cotton','groundnut','red_gram'],
    minAcres: 0, maxAcres: 999,
    category: 'input',
    apply: 'AP Horticulture Department / MIDH portal',
    color: 'forest',
  },
  {
    id: 'soil_health',
    name: 'Soil Health Card Scheme',
    te: 'నేల ఆరోగ్య కార్డు',
    benefit: 'Free soil testing + advisory',
    description: 'Free soil testing every 2 years with nutrient recommendations. Reduces fertilizer cost by 10-20%.',
    eligibility: ['All farmers', 'No land restriction'],
    crops: ['paddy','cotton','groundnut','red_gram'],
    minAcres: 0, maxAcres: 999,
    category: 'advisory',
    apply: 'Nearest Krishi Vigyan Kendra / Agriculture office',
    color: 'forest',
  },
  {
    id: 'kcc',
    name: 'Kisan Credit Card',
    te: 'కిసాన్ క్రెడిట్ కార్డ్',
    benefit: 'Credit up to ₹3 lakh at 4% interest',
    description: 'Short-term credit for seasonal inputs. Interest subvention brings effective rate to 4% for timely repayment.',
    eligibility: ['Land-owning or tenant farmers', 'Valid land documents', 'Bank account'],
    crops: ['paddy','cotton','groundnut','red_gram'],
    minAcres: 0, maxAcres: 999,
    category: 'credit',
    apply: 'Any nationalized bank / Cooperative bank',
    color: 'amber',
  },
  {
    id: 'enam',
    name: 'eNAM Market Platform',
    te: 'ఇ-నామ్',
    benefit: 'Better price discovery, direct market access',
    description: 'Electronic National Agriculture Market — sell produce online across India. Better prices than local mandis.',
    eligibility: ['Any farmer', 'Produce must be graded', 'Enrol at local mandi'],
    crops: ['paddy','cotton','groundnut','red_gram'],
    minAcres: 0, maxAcres: 999,
    category: 'market',
    apply: 'enam.gov.in / Local APMC mandi',
    color: 'amber',
  },
  {
    id: 'organic',
    name: 'Paramparagat Krishi Vikas Yojana',
    te: 'సేంద్రియ వ్యవసాయం',
    benefit: '₹50,000/ha over 3 years for organic farming',
    description: 'Support for conversion to organic farming. Covers inputs, certification, and market linkage.',
    eligibility: ['Minimum 5 ha cluster', 'Commit to 3-year organic transition', 'PGS certification'],
    crops: ['paddy','groundnut','red_gram'],
    minAcres: 12, maxAcres: 999,
    category: 'organic',
    apply: 'District Agriculture Office / PKVY portal',
    color: 'forest',
  },
]

const CROP_OPTIONS = [
  { key: 'all', label: 'All Crops' },
  { key: 'paddy', label: 'Paddy' },
  { key: 'cotton', label: 'Cotton' },
  { key: 'groundnut', label: 'Groundnut' },
  { key: 'red_gram', label: 'Red Gram' },
]

const CATEGORY_OPTIONS = [
  { key: 'all', label: 'All' },
  { key: 'income', label: 'Income' },
  { key: 'insurance', label: 'Insurance' },
  { key: 'input', label: 'Input' },
  { key: 'credit', label: 'Credit' },
  { key: 'market', label: 'Market' },
  { key: 'organic', label: 'Organic' },
  { key: 'advisory', label: 'Advisory' },
]

const borderColors = {
  forest: 'border-l-4 border-l-green-700',
  amber: 'border-l-4 border-l-amber-500',
}

const bgColors = {
  forest: 'bg-green-50',
  amber: 'bg-amber-50',
}

export default function GovSchemes() {
  const [selectedCrop, setSelectedCrop] = useState('all')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [area, setArea] = useState(2)
  const [expandedId, setExpandedId] = useState(null)

  const filtered = SCHEMES.filter(s => {
    const cropMatch = selectedCrop === 'all' || s.crops.includes(selectedCrop)
    const catMatch = selectedCategory === 'all' || s.category === selectedCategory
    return cropMatch && catMatch
  })

  const eligible = filtered.filter(s => area >= s.minAcres && area <= s.maxAcres)

  return (
    <div className="flex flex-col gap-6">
      <div className="card">
        <div className="card-header">
          <span className="text-base mr-2">🏛</span>
          <span className="font-semibold text-earth-900">Government Scheme Finder</span>
          <span className="ml-2 text-[10px] text-earth-500">ప్రభుత్వ పథకాలు</span>
        </div>
        <div className="px-5 py-4 flex flex-col gap-4">
          <div className="flex flex-col gap-3">
            <div>
              <span className="section-title">Crop</span>
              <div className="flex flex-wrap gap-2 mt-2">
                {CROP_OPTIONS.map(c => (
                  <button
                    key={c.key}
                    onClick={() => setSelectedCrop(c.key)}
                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                      selectedCrop === c.key
                        ? 'bg-green-800 text-white border-green-800'
                        : 'bg-white text-earth-700 border-earth-200 hover:border-green-600 hover:text-green-700'
                    }`}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <span className="section-title">Category</span>
              <div className="flex flex-wrap gap-2 mt-2">
                {CATEGORY_OPTIONS.map(c => (
                  <button
                    key={c.key}
                    onClick={() => setSelectedCategory(c.key)}
                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                      selectedCategory === c.key
                        ? 'bg-earth-700 text-white border-earth-700'
                        : 'bg-white text-earth-700 border-earth-200 hover:border-earth-500 hover:text-earth-900'
                    }`}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="max-w-xs">
              <label className="section-title block mb-1">Your landholding (acres)</label>
              <input
                type="number"
                min={0}
                max={999}
                value={area}
                onChange={e => setArea(Number(e.target.value))}
                className="field-input"
              />
            </div>
          </div>

          <div className="flex items-center gap-2 py-2 px-3 bg-green-50 rounded-xl border border-green-100">
            <span className="text-green-700 font-semibold text-sm">
              You are eligible for {eligible.length} of {filtered.length} schemes
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filtered.map(scheme => {
          const isExpanded = expandedId === scheme.id
          const meetsArea = area >= scheme.minAcres

          return (
            <div
              key={scheme.id}
              onClick={() => setExpandedId(isExpanded ? null : scheme.id)}
              className={`card cursor-pointer ${borderColors[scheme.color]} transition-all hover:shadow-md`}
            >
              <div className="px-5 py-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-col gap-0.5">
                    <span className="font-semibold text-earth-900 text-sm">{scheme.name}</span>
                    <span className="text-[11px] text-earth-500">{scheme.te}</span>
                  </div>
                  <span className="shrink-0 bg-green-100 text-green-800 text-[10px] font-semibold px-2 py-1 rounded-full whitespace-nowrap">
                    {scheme.benefit}
                  </span>
                </div>
                <p className="text-xs text-earth-600 mt-2 line-clamp-2">{scheme.description}</p>

                {!meetsArea && (
                  <div className="mt-2 flex items-center gap-1 text-amber-700 text-[11px] font-medium">
                    <span>⚠</span>
                    <span>Minimum {scheme.minAcres} acres required</span>
                  </div>
                )}

                {isExpanded && (
                  <div className="mt-4 flex flex-col gap-3 border-t border-earth-100 pt-3">
                    <div>
                      <span className="section-title">Eligibility</span>
                      <ul className="mt-2 flex flex-col gap-1">
                        {scheme.eligibility.map((item, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-earth-700">
                            <span className="text-green-600 mt-0.5">✓</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <span className="section-title">How to Apply</span>
                      <p className="mt-1 text-xs text-earth-700">{scheme.apply}</p>
                    </div>
                    <button
                      onClick={e => e.stopPropagation()}
                      className="self-start mt-1 px-4 py-2 bg-green-800 text-white text-xs font-semibold rounded-xl hover:bg-green-700 transition-colors"
                    >
                      Apply Now
                    </button>
                  </div>
                )}

                <div className="mt-3 flex items-center justify-end">
                  <span className="text-[10px] text-earth-400">{isExpanded ? 'Click to collapse ▲' : 'Click for details ▼'}</span>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
