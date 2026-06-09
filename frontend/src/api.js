const BASE = '/api'

export const SOIL_PARAMS = ['pH', 'EC', 'OC', 'N', 'P', 'K', 'Fe', 'Cu', 'B', 'Zn']
export const DEFAULT_WINDOW = 'post_kharif_2024'

export const PARAM_LABELS = {
  pH: 'Soil pH', EC: 'EC (dS/m)', OC: 'Organic Carbon (%)',
  N: 'Available N (kg/ha)', P: 'Available P (kg/ha)', K: 'Available K (kg/ha)',
  Fe: 'Iron (ppm)', Cu: 'Copper (ppm)', B: 'Boron (ppm)', Zn: 'Zinc (ppm)',
}
export const PARAM_UNITS = {
  pH: '', EC: 'dS/m', OC: '%',
  N: 'kg/ha', P: 'kg/ha', K: 'kg/ha',
  Fe: 'ppm', Cu: 'ppm', B: 'ppm', Zn: 'ppm',
}
// EC is "bad when high" — invert color scale
export const INVERTED_PARAMS = new Set(['EC'])

export const CROPS = {
  paddy:     'Paddy (వరి)',
  cotton:    'Cotton (పత్తి)',
  groundnut: 'Groundnut (వేరుసెనగ)',
  red_gram:  'Red Gram (కందులు)',
}
export const DEFAULT_YIELDS = {
  paddy: 5.5, cotton: 2.0, groundnut: 2.5, red_gram: 1.5,
}

async function get(url) {
  const r = await fetch(BASE + url)
  if (!r.ok) return null
  return r.json()
}

export async function fetchMapStats(param, window = DEFAULT_WINDOW) {
  return get(`/maps/${param}/stats?window=${window}`)
}

export async function fetchAllStats(window = DEFAULT_WINDOW) {
  const results = await Promise.allSettled(
    SOIL_PARAMS.map(p => fetchMapStats(p, window))
  )
  const out = {}
  SOIL_PARAMS.forEach((p, i) => {
    if (results[i].status === 'fulfilled' && results[i].value) {
      out[p] = results[i].value
    }
  })
  return out
}

export async function fetchMapPoints(param, n = 2000, window = DEFAULT_WINDOW) {
  return get(`/maps/${param}/points?n=${n}&window=${window}`)
}

export async function fetchSuitability(soil) {
  const r = await fetch(`${BASE}/suitability`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(soil),
  })
  if (!r.ok) return null
  return r.json()
}

export async function fetchWeatherTiming(lat = 16.35, lon = 80.75) {
  return get(`/weather/timing?lat=${lat}&lon=${lon}`)
}

export async function postRecommendation(body) {
  const r = await fetch(`${BASE}/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await r.json()
  if (!r.ok) throw new Error(data.detail || 'Request failed')
  return data
}
