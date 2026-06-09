# AI-Enabled Soil Nutrient Mapping & Advisory System

Hackathon project for the Agriculture Department, Government of Andhra Pradesh. The goal is to win by building a scientifically rigorous, production-ready system that generates confidence-scored soil health maps and crop-specific fertilizer recommendations using satellite imagery fused with Soil Health Card data.

## Project Goals

- Generate field-level soil health maps for pH, EC, and Organic Carbon (primary deliverables)
- Generate nutrient maps for N, P, K, Fe, Cu, B, Zn with calibrated confidence scores (stretch deliverables)
- Deliver a fertilizer recommendation engine calibrated to ICAR guidelines for AP
- Build a decision support dashboard for agriculture officials and a farmer-facing interface in Telugu and English
- Focus crops: paddy, cotton, groundnut, red gram

## Architecture

The system has six layers:

1. **Satellite Data Pipeline** — Google Earth Engine scripts to generate bare-soil composites from Sentinel-2 L2A (NDVI < 0.25 masking), Planet 3m composites, Landsat thermal, and PRISMA/EnMAP hyperspectral. Compute 40+ spectral indices (BSI, clay index, iron index, NDRE, salinity indices) and terrain features from SRTM DEM (TWI, slope, curvature).

2. **Feature Engineering** — Combine spectral indices, terrain derivatives, and APSAC legacy soil map attributes into an ~80-feature stack per parcel. Georeference Soil Health Card training labels with 100m buffer averaging to match satellite resolution.

3. **ML Ensemble** — Three models trained with spatial k-fold cross-validation (not random split — critical for avoiding spatial data leakage):
   - CatBoost + MAPIE conformal prediction (primary, gives coverage-guaranteed intervals)
   - Gaussian Process Regressor via GPyTorch (uncertainty-native, sparse GP for scale)
   - Quantile Random Forest (fallback, handles asymmetric uncertainty)
   Ensemble weighted by calibration error. For micronutrients with sparse labels, use semi-supervised graph diffusion on spatial similarity graphs.

4. **Map Generation** — Predict all soil parameters per pixel/parcel, output confidence intervals and scores. Serve as Cloud-Optimized GeoTIFFs and vector tiles via PostGIS + pg_tileserv.

5. **Fertilizer Recommendation Engine** — Nutrient balance method: `Dose = (Crop Requirement - Soil Supply) / Fertilizer Use Efficiency`. Uses ICAR-published tables for AP. Outputs basal and split-dose schedules per field and crop, with estimated cost savings vs. blanket application.

6. **User Interfaces** — React + Mapbox GL JS dashboard for officials (choropleth maps, confidence overlays, trend analysis, adoption tracking). React Native farmer app (offline-capable, Telugu/English). SMS output for feature phones.

## Tech Stack

- **Satellite processing**: Google Earth Engine (Python API)
- **Geospatial**: GDAL, Rasterio, GeoPandas, Shapely
- **ML**: CatBoost, GPyTorch, scikit-learn, MAPIE
- **Database**: PostGIS (PostgreSQL)
- **Backend**: FastAPI (Python)
- **Frontend**: React, Mapbox GL JS, Recharts
- **Mobile**: React Native
- **Tile server**: pg_tileserv or Martin
- **Deployment**: Docker Compose

## Project Structure

```
soil-advisory/
├── gee/            # Google Earth Engine scripts
├── pipeline/       # Data ingest, feature engineering, training, prediction
├── backend/        # FastAPI app, PostGIS models, API routes
├── frontend/       # React dashboard + React Native farmer app
└── docs/           # Methodology writeup for judges
```

## Key Differentiators

- **Conformal prediction** for calibrated uncertainty — not hacked standard deviations
- **Spatial k-fold CV** to report honest accuracy metrics judges can verify
- **PRISMA hyperspectral** integration for clay mineralogy and micronutrient proxies
- **Telugu localization** throughout the farmer interface
- **Semi-supervised learning** for micronutrients where SHC coverage is sparse

## Coding Conventions

- All geospatial data in EPSG:32644 (UTM Zone 44N, covers AP) internally; reproject to EPSG:4326 only at API boundaries
- All rasters saved as Cloud-Optimized GeoTIFF with LZW compression
- FastAPI routes return GeoJSON for vector data, URLs for raster tiles
- Never hardcode fertilizer values — all crop/nutrient tables live in `pipeline/fertilizer_tables.py`
- Model artifacts saved with the CV fold metrics embedded in the filename
