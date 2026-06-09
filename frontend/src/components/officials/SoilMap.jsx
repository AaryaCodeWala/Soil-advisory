import { useEffect, useState, useMemo } from 'react'
import { MapContainer, TileLayer, ImageOverlay, GeoJSON, CircleMarker, Tooltip, useMap } from 'react-leaflet'
import { fetchMapPoints, PARAM_LABELS, PARAM_UNITS, INVERTED_PARAMS } from '../../api'
import krishnaGeoJSON from '../../data/krishna_district.json'

const BOUNDS = [[15.65, 80.58], [16.82, 81.62]]
const CENTER = [16.235, 81.1]
const OVERLAY_OPACITY = 0.72

function classColor(cls) {
  if (!cls) return '#facc15'
  const c = cls.toLowerCase()
  if (c === 'deficient' || c === 'acid' || c === 'alkaline' || c === 'low') return '#ef4444'
  if (c === 'medium' || c === 'moderate') return '#f97316'
  return '#22c55e'
}

function MapResizer() {
  const map = useMap()
  useEffect(() => {
    setTimeout(() => map.invalidateSize(), 100)
  }, [map])
  return null
}

function SampleDot({ lat, lon, val, cls, label, unit, isConf }) {
  return (
    <CircleMarker
      center={[lat, lon]}
      radius={4}
      pathOptions={{
        fillColor: classColor(cls),
        fillOpacity: 0.85,
        color: '#fff',
        weight: 0.8,
        opacity: 1,
      }}
    >
      <Tooltip sticky direction="top" offset={[0, -4]} opacity={0.97}>
        <div style={{ fontSize: 11 }}>
          <div style={{ fontWeight: 700, color: '#2D4A38' }}>{label}</div>
          <div style={{ fontWeight: 600, color: '#1A3528', fontSize: 12 }}>
            {isConf ? `${(val * 100).toFixed(1)}%` : `${val.toFixed(3)}${unit ? ' ' + unit : ''}`}
          </div>
          {cls && <div style={{ color: '#777', textTransform: 'capitalize' }}>{cls}</div>}
        </div>
      </Tooltip>
    </CircleMarker>
  )
}

export default function SoilMap({ param, layer }) {
  const [imgKey,  setImgKey]  = useState(0)
  const [imgUrl,  setImgUrl]  = useState(null)
  const [points,  setPoints]  = useState(null)
  const [loading, setLoading] = useState(true)

  const inverted = INVERTED_PARAMS.has(param) && layer === 'value'
  const layerStr = layer === 'confidence' ? 'confidence' : 'prediction'
  const unit     = PARAM_UNITS[param]
  const label    = layer === 'confidence' ? 'Confidence' : PARAM_LABELS[param]
  const isConf   = layer === 'confidence'

  useEffect(() => {
    setLoading(true)
    setImgUrl(null)
    setImgKey(k => k + 1)
    const url = `/api/maps/${param}/raster.png?layer=${layerStr}&invert=${inverted}&window=combined&_=${Date.now()}`
    const img = new Image()
    img.onload  = () => { setImgUrl(url); setLoading(false) }
    img.onerror = () => { setImgUrl(null); setLoading(false) }
    img.src = url
  }, [param, layer])

  useEffect(() => {
    setPoints(null)
    fetchMapPoints(param, 1200, 'combined')
      .then(data => setPoints(data))
      .catch(() => null)
  }, [param])

  const features = useMemo(() => {
    if (!points?.features?.length) return []
    return points.features.map(f => ({
      lat: f.geometry.coordinates[1],
      lon: f.geometry.coordinates[0],
      val: isConf ? (f.properties.confidence ?? 0) : f.properties.value,
      cls: f.properties.class,
    }))
  }, [points, layer])

  const districtStyle = { color: '#4ade80', weight: 2, fillOpacity: 0 }

  return (
    <div className="relative h-full w-full rounded-xl overflow-hidden">
      {loading && (
        <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-earth-900/60 backdrop-blur-sm rounded-xl">
          <div className="flex flex-col items-center gap-3">
            <div className="w-7 h-7 rounded-full border-2 border-green-400 border-t-transparent animate-spin" />
            <span className="text-xs text-white/80">Loading satellite map…</span>
          </div>
        </div>
      )}

      <MapContainer
        key={`map-${param}`}
        center={CENTER}
        zoom={9}
        bounds={BOUNDS}
        scrollWheelZoom={true}
        zoomControl={true}
        attributionControl={false}
        style={{ height: '100%', width: '100%', background: '#1a1a2e' }}
      >
        <MapResizer />

        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution="ESRI World Imagery"
          maxZoom={18}
        />

        {imgUrl && (
          <ImageOverlay
            key={imgKey}
            url={imgUrl}
            bounds={BOUNDS}
            opacity={OVERLAY_OPACITY}
          />
        )}

        <GeoJSON data={krishnaGeoJSON} style={districtStyle} />

        {features.map((f, i) => (
          <SampleDot
            key={i}
            lat={f.lat}
            lon={f.lon}
            val={f.val}
            cls={f.cls}
            label={label}
            unit={unit}
            isConf={isConf}
          />
        ))}
      </MapContainer>

      {!loading && imgUrl && (
        <div className="absolute bottom-8 right-3 z-[999] bg-black/70 backdrop-blur-sm rounded-xl border border-white/20 px-3 py-2.5">
          <p className="text-[10px] font-semibold text-white/60 uppercase tracking-wider mb-1.5">{label}</p>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-red-400 font-medium">Low</span>
            <div
              className="h-2.5 w-24 rounded-full"
              style={{ background: 'linear-gradient(to right, #d73027, #fc8d59, #fee08b, #91cf60, #1a9850)' }}
            />
            <span className="text-[10px] text-green-400 font-medium">High</span>
          </div>
          {unit && <p className="text-[9px] text-white/40 mt-0.5">Unit: {unit}</p>}
        </div>
      )}
    </div>
  )
}
