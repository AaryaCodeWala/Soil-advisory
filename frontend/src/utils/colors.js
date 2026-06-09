// RdYlGn color scale (red = bad, green = good)
const STOPS = [
  [0,    [198, 40,  40]],   // dark red
  [0.25, [239, 108, 0]],    // orange
  [0.5,  [249, 168, 37]],   // amber
  [0.75, [85,  139, 47]],   // light green
  [1,    [27,  94,  32]],   // dark green
]

function lerp(a, b, t) { return Math.round(a + (b - a) * t) }

export function scaleColor(normValue, inverted = false) {
  const v = Math.max(0, Math.min(1, inverted ? 1 - normValue : normValue))
  let i = 0
  while (i < STOPS.length - 2 && v > STOPS[i + 1][0]) i++
  const [t0, c0] = STOPS[i]
  const [t1, c1] = STOPS[i + 1]
  const frac = (v - t0) / (t1 - t0)
  const [r, g, b] = [0, 1, 2].map(j => lerp(c0[j], c1[j], frac))
  return `rgb(${r},${g},${b})`
}

export function confColor(conf) {
  if (conf >= 0.75) return '#2e7d32'
  if (conf >= 0.5)  return '#e65100'
  return '#c62828'
}

export function defColor(pct) {
  if (pct > 60) return 'text-red-700 bg-red-50'
  if (pct > 30) return 'text-amber-700 bg-amber-50'
  return 'text-green-700 bg-green-50'
}
