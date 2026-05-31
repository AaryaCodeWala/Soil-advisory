/**
 * Terrain Feature Derivation from SRTM DEM — Andhra Pradesh
 *
 * Computes: elevation, slope, aspect, hillshade, plan/profile curvature,
 * Topographic Wetness Index (TWI), TRI, TPI.
 *
 * TWI = ln(flow_accumulation / tan(slope)) — key predictor for OC, EC,
 * and clay content because it controls water redistribution across landscape.
 *
 * Run in GEE Code Editor after sentinel2_composite.js.
 * Export to the same Drive folder at 30 m, then resample in Python pipeline.
 */

// ── AOI (same as sentinel2_composite.js) ─────────────────────────────────────

var pilotDistrict = ee.FeatureCollection('FAO/GAUL/2015/level2')
  .filter(ee.Filter.and(
    ee.Filter.eq('ADM1_NAME', 'Andhra Pradesh'),
    ee.Filter.eq('ADM2_NAME', 'Krishna')
  ));
var AOI = pilotDistrict.geometry();

// ── DEM ──────────────────────────────────────────────────────────────────────

var dem = ee.Image('USGS/SRTMGL1_003').clip(AOI);  // 30 m SRTM

// ── Basic derivatives ────────────────────────────────────────────────────────

var slope     = ee.Terrain.slope(dem).rename('slope');        // degrees
var aspect    = ee.Terrain.aspect(dem).rename('aspect');      // degrees 0-360
var hillshade = ee.Terrain.hillshade(dem).rename('hillshade');

// ── Curvature (plan + profile) ───────────────────────────────────────────────
// GEE doesn't expose curvature natively; compute via finite differences on DEM.

var pixelSize = ee.Number(30);  // SRTM native resolution

// Kernel to get 3×3 neighbourhood elevation values
var kernel = ee.Kernel.fixed({
  width: 3, height: 3,
  weights: [[1,1,1],[1,1,1],[1,1,1]],
  x: 1, y: 1, normalize: false
});

// Zevenbergen & Thorne (1987) curvature via neighbour differences
var z = dem.neighborhoodToArray(kernel);  // not straightforward in GEE
// Simpler GEE approach: use Laplacian of Gaussian as curvature proxy
var laplacian = dem.convolve(ee.Kernel.laplacian8()).rename('curvature');

// Plan curvature: perpendicular to slope direction (controls lateral water flow)
var planCurv = dem.convolve(
  ee.Kernel.fixed(3, 3,
    [[0, -1, 0],
     [-1, 4, -1],
     [0, -1, 0]])
).rename('plan_curvature');

// Profile curvature: along slope direction (controls flow acceleration)
var profileCurv = dem.convolve(
  ee.Kernel.fixed(3, 3,
    [[-1, -1, -1],
     [0,  0,  0],
     [1,  1,  1]])
).rename('profile_curvature');

// ── Topographic Wetness Index (TWI) ──────────────────────────────────────────
// TWI = ln(a / tan(β))  where a = specific catchment area, β = slope in radians
// GEE doesn't have D8 flow accumulation; use DEM-based proxy:
//   a ≈ flow accumulation approximated by local relief upslope area

// Convert slope to radians, floor at 0.001 to avoid ln(0)
var slopeRad = slope.multiply(Math.PI / 180).max(0.001);
var tanSlope = slopeRad.tan().max(0.001);

// Specific catchment area proxy: use focal_mean over 5×5 to capture upslope contrib
var fcArea = dem.focalMean({radius: 5, kernelType: 'square', units: 'pixels'})
  .subtract(dem).abs().add(1).rename('upslope_proxy');

var twi = fcArea.divide(tanSlope).log().rename('TWI');

// ── Terrain Ruggedness Index (TRI) ───────────────────────────────────────────
// TRI = mean absolute difference of each cell from its 8 neighbours
var demNeighbours = dem.neighborhoodToBands(ee.Kernel.square(1));
var tri = demNeighbours.subtract(dem).abs().reduce(ee.Reducer.mean()).rename('TRI');

// ── Topographic Position Index (TPI) ─────────────────────────────────────────
// TPI = elevation - mean elevation in neighbourhood (300 m window ≈ 10 pixels)
var focalMean300 = dem.focalMean({radius: 10, kernelType: 'square', units: 'pixels'});
var tpi = dem.subtract(focalMean300).rename('TPI');

// ── Stack all terrain features ───────────────────────────────────────────────

var terrainStack = dem.rename('elevation')
  .addBands(slope)
  .addBands(aspect)
  .addBands(hillshade)
  .addBands(laplacian)
  .addBands(planCurv)
  .addBands(profileCurv)
  .addBands(twi)
  .addBands(tri)
  .addBands(tpi);

// ── Visualise ────────────────────────────────────────────────────────────────

Map.centerObject(AOI, 9);
Map.addLayer(dem,          {min: 0, max: 400, palette: ['green','yellow','brown','white']}, 'Elevation');
Map.addLayer(slope,        {min: 0, max: 30,  palette: ['white','orange','red']}, 'Slope');
Map.addLayer(twi,          {min: 4, max: 12,  palette: ['red','white','blue']}, 'TWI');
Map.addLayer(tpi,          {min: -20, max: 20, palette: ['blue','white','red']}, 'TPI');

// ── Export ───────────────────────────────────────────────────────────────────

Export.image.toDrive({
  image: terrainStack.toFloat(),
  description: 'TerrainFeatures_Krishna_SRTM30m',
  folder: 'SoilHackathon_GEE',
  fileNamePrefix: 'terrain_features_krishna_srtm',
  region: AOI,
  scale: 30,           // export at native SRTM 30 m; resample to 10 m in Python
  crs: 'EPSG:32644',
  maxPixels: 1e10,
  fileFormat: 'GeoTIFF',
});

print('Terrain export submitted.');
