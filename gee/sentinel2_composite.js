/**
 * Sentinel-2 Bare-Soil Composite — Andhra Pradesh
 *
 * Run this in the GEE Code Editor (code.earthengine.google.com).
 * Outputs a median bare-soil composite with all spectral indices
 * exported to Google Drive as a Cloud-Optimised GeoTIFF.
 *
 * Projection: EPSG:32644 (UTM Zone 44N)  Resolution: 10 m
 */

// ── 1. Region of interest ────────────────────────────────────────────────────

// Full AP boundary from FAO GAUL admin-1
var ap = ee.FeatureCollection('FAO/GAUL/2015/level1')
  .filter(ee.Filter.eq('ADM1_NAME', 'Andhra Pradesh'));

// Pilot district (Krishna) — swap to ap for full-state export
var pilotDistrict = ee.FeatureCollection('FAO/GAUL/2015/level2')
  .filter(ee.Filter.and(
    ee.Filter.eq('ADM1_NAME', 'Andhra Pradesh'),
    ee.Filter.eq('ADM2_NAME', 'Krishna')
  ));

var AOI = pilotDistrict.geometry();
Map.centerObject(AOI, 9);

// ── 2. Cloud masking ─────────────────────────────────────────────────────────

function maskS2clouds(image) {
  var scl = image.select('SCL');
  // SCL classes to keep: 4=vegetation, 5=bare soil, 6=water, 11=snow (rare in AP)
  // Remove: 1=saturated, 2=dark, 3=shadow, 7=unclassified, 8=medium cloud,
  //         9=high cloud, 10=cirrus
  var goodPixels = scl.eq(4).or(scl.eq(5)).or(scl.eq(6));
  return image.updateMask(goodPixels).divide(10000)  // scale to reflectance
    .copyProperties(image, ['system:time_start']);
}

// ── 3. Bare-soil NDVI filter ─────────────────────────────────────────────────

function keepBareSoil(image) {
  var ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI');
  var bareMask = ndvi.lt(0.25);  // bare soil / sparsely vegetated
  return image.updateMask(bareMask);
}

// ── 4. Spectral indices ──────────────────────────────────────────────────────

function addIndices(image) {
  var blue  = image.select('B2');
  var green = image.select('B3');
  var red   = image.select('B4');
  var re1   = image.select('B5');   // Red-edge 1 (705 nm)
  var nir   = image.select('B8');   // NIR broad (842 nm)
  var swir1 = image.select('B11');  // SWIR 1 (1610 nm)
  var swir2 = image.select('B12');  // SWIR 2 (2190 nm)

  // Vegetation / soil baseline
  var ndvi  = nir.subtract(red).divide(nir.add(red)).rename('NDVI');
  var savi  = nir.subtract(red).divide(nir.add(red).add(0.5)).multiply(1.5).rename('SAVI');
  var evi2  = nir.subtract(red).divide(nir.add(red.multiply(2.4)).add(1)).multiply(2.5).rename('EVI2');

  // MSAVI2: self-adjusting soil line, better than SAVI for bare soil
  var msavi2 = nir.multiply(2).add(1)
    .subtract(
      nir.multiply(2).add(1).pow(2)
        .subtract(nir.subtract(red).multiply(8))
        .sqrt()
    ).divide(2).rename('MSAVI2');

  // Bare Soil Index — separates bare soil from vegetation
  var bsi = swir1.add(red).subtract(nir.add(blue))
    .divide(swir1.add(red).add(nir).add(blue)).rename('BSI');

  // Red-edge NDVI — sensitive to chlorophyll, inverted for bare soil work
  var ndre = re1.subtract(red).divide(re1.add(red)).rename('NDRE');

  // Water index (helps mask residual water pixels)
  var ndwi = green.subtract(nir).divide(green.add(nir)).rename('NDWI');

  // Brightness Index — proxy for reflectance magnitude (correlated with EC)
  var bi = red.pow(2).add(green.pow(2)).add(nir.pow(2))
    .divide(3).sqrt().rename('BI');

  // ── Salinity / EC proxies ────────────────────────────────────────────────
  // SI1: simple salinity index from green & red
  var si1 = green.multiply(red).sqrt().rename('SI1');
  // SI2: SWIR-based salinity (saline soils bright in SWIR)
  var si2 = swir1.subtract(nir).divide(swir1.add(nir)).rename('SI2');
  // NDSI soil (not snow): difference in SWIR bands
  var ndsi = swir1.subtract(swir2).divide(swir1.add(swir2)).rename('NDSI');

  // ── Clay / mineralogy proxies (pH correlates) ────────────────────────────
  // Clay Index: ratio at 2.2 / 1.6 μm — kaolinite/illite absorption at 2.2
  var clayIndex = swir1.divide(swir2).rename('ClayIndex');
  // AlOH Index: sensitive to Al-OH stretch at 2.2 μm vs baseline at 1.6
  var aloh = swir1.divide(swir2).rename('AlOH');  // same ratio, different name in literature
  // Carbonate Index: CaCO3 absorption at 2.35 μm (approximated with S2 SWIR2)
  var carbonate = swir1.divide(swir2.add(nir.multiply(0.1))).rename('CarbonateIndex');

  // ── Iron / micronutrient proxies ─────────────────────────────────────────
  // Iron Index: iron oxides absorb strongly in blue, reflect in red
  var ironIndex = red.divide(blue).rename('IronIndex');
  // Ferrous Index: Fe2+ sensitive to NIR/SWIR ratio
  var ferrousIndex = nir.divide(swir1).rename('FerrousIndex');
  // Redness Index: Fe-oxide laterites
  var ri = red.pow(2).divide(blue.multiply(green.pow(3))).rename('RI');

  // ── Other composite ratios ───────────────────────────────────────────────
  var swirRatio    = swir1.divide(swir2).rename('SWIR_ratio');
  var reRatio      = re1.divide(red).rename('RedEdge_ratio');
  // Chlorophyll Index green — proxy for organic carbon via crop residue
  var ciGreen      = nir.divide(green).subtract(1).rename('CI_green');

  return image.addBands([
    ndvi, savi, evi2, msavi2, bsi,
    ndre, ndwi, bi,
    si1, si2, ndsi,
    clayIndex, aloh, carbonate,
    ironIndex, ferrousIndex, ri,
    swirRatio, reRatio, ciGreen
  ]);
}

// ── 5. Build composites for each bare-soil window ────────────────────────────

var windows = [
  {start: '2024-11-01', end: '2025-02-28', label: 'post_kharif_2024'},
  {start: '2024-03-15', end: '2024-06-15', label: 'pre_monsoon_2024'},
];

var composites = windows.map(function(w) {
  var col = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(AOI)
    .filterDate(w.start, w.end)
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
    .map(maskS2clouds)
    .map(keepBareSoil)
    .map(addIndices);

  var composite = col.median().clip(AOI);
  print('Scene count ' + w.label + ':', col.size());
  return composite.set('label', w.label);
});

// ── 6. Primary composite: post-Kharif (best bare soil in AP) ─────────────────

var primaryComposite = ee.Image(composites[0]);

// Select the bands to export (raw S2 + all indices)
var exportBands = [
  'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12',
  'NDVI', 'BSI', 'SAVI', 'MSAVI2', 'EVI2',
  'NDRE', 'NDWI', 'BI',
  'SI1', 'SI2', 'NDSI',
  'ClayIndex', 'AlOH', 'CarbonateIndex',
  'IronIndex', 'FerrousIndex', 'RI',
  'SWIR_ratio', 'RedEdge_ratio', 'CI_green'
];

// ── 7. Visualisation ─────────────────────────────────────────────────────────

Map.addLayer(primaryComposite, {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.3}, 'True Colour');
Map.addLayer(primaryComposite, {bands: ['B8', 'B4', 'B3'], min: 0, max: 0.4}, 'False Colour NIR');
Map.addLayer(primaryComposite.select('BSI'), {min: -0.5, max: 0.5, palette: ['blue', 'white', 'brown']}, 'BSI');
Map.addLayer(primaryComposite.select('ClayIndex'), {min: 0.8, max: 1.3, palette: ['white', 'orange', 'red']}, 'Clay Index');
Map.addLayer(primaryComposite.select('IronIndex'), {min: 1, max: 4, palette: ['white', 'yellow', 'red']}, 'Iron Index');

// ── 8. Export ────────────────────────────────────────────────────────────────

Export.image.toDrive({
  image: primaryComposite.select(exportBands).toFloat(),
  description: 'S2_BaresoilComposite_Krishna_PostKharif2024',
  folder: 'SoilHackathon_GEE',
  fileNamePrefix: 's2_baresoil_krishna_post_kharif_2024',
  region: AOI,
  scale: 10,
  crs: 'EPSG:32644',
  maxPixels: 1e10,
  fileFormat: 'GeoTIFF',
});

// Export secondary composite for temporal comparison
Export.image.toDrive({
  image: ee.Image(composites[1]).select(exportBands).toFloat(),
  description: 'S2_BaresoilComposite_Krishna_PreMonsoon2024',
  folder: 'SoilHackathon_GEE',
  fileNamePrefix: 's2_baresoil_krishna_pre_monsoon_2024',
  region: AOI,
  scale: 10,
  crs: 'EPSG:32644',
  maxPixels: 1e10,
  fileFormat: 'GeoTIFF',
});

print('Exports submitted. Check Tasks tab.');
