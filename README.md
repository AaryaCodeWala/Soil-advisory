# AI-Enabled Soil Nutrient Mapping & Advisory System
**Agriculture Department, Government of Andhra Pradesh — Hackathon Submission**

Field-level soil health maps for Krishna District with calibrated confidence intervals and ICAR-compliant fertilizer recommendations for paddy, cotton, groundnut, and red gram.

---

## Live Demo

| Service | URL |
|---------|-----|
| **React Dashboard** | http://localhost:3000 |
| **FastAPI Backend** | http://localhost:8000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Backend

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

pip install -r requirements.txt

uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**

---

## What the System Produces

| Output | Description |
|--------|-------------|
| **10 soil parameter maps** | pH, EC, OC, N, P, K, Fe, Cu, B, Zn — Krishna District at 100 m |
| **Confidence intervals** | 90% prediction intervals per pixel (conformal-guaranteed via MAPIE) |
| **Confidence scores** | 0–1 score per pixel gating advisory outputs |
| **Deficiency class maps** | ICAR-classified low/medium/high per pixel |
| **Fertilizer advisory** | ICAR nutrient balance method, 4 crops, site-specific doses |
| **Bilingual SMS** | English + Telugu output, feature-phone ready |
| **Satellite choropleth** | ESRI satellite imagery + soil overlay with hover tooltips |

---

## Repository Layout

```
soil-advisory/
├── pipeline/
│   ├── config.py                   # AOI, CRS, parameter list
│   ├── 01_data_ingest.py           # GEE Sentinel-2 download
│   ├── 02_feature_engineering.py   # 40+ band feature stack
│   ├── 03_train_models.py          # CatBoost+MAPIE, GPR, Quantile RF
│   ├── 04_extract_training_data.py # SHC → feature vector alignment
│   ├── 05_predict_maps.py          # Pixel-level inference → GeoTIFFs
│   ├── fertilizer_tables.py        # All ICAR crop/nutrient tables
│   ├── generate_synthetic_data.py  # Synthetic SHC augmentation
│   └── crop_suitability.py         # ICAR threshold-based crop scoring
├── backend/
│   ├── main.py                     # FastAPI app
│   └── routers/
│       ├── maps.py                 # stats, points, raster PNG endpoints
│       ├── recommendations.py      # POST /api/recommend
│       ├── suitability.py          # POST /api/suitability
│       ├── weather.py              # GET /api/weather/timing (Open-Meteo)
│       └── sms.py                  # POST /api/sms
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── officials/          # District dashboard (satellite map, KPIs, charts)
│   │   │   ├── farmer/             # Farmer portal (advisory, yield, pest, irrigation)
│   │   │   └── admin/              # State admin view
│   │   ├── App.jsx
│   │   └── api.js
│   ├── package.json
│   └── vite.config.js
├── data/
│   ├── models/                     # Trained MAPIE + QRF artifacts + meta JSON
│   └── processed/
│       ├── combined_training_data.csv
│       └── maps/                   # Prediction GeoTIFFs (regenerate if missing)
├── colab_train.ipynb               # GPU training fallback (Google Colab)
└── requirements.txt
```

---

## Regenerating Prediction Maps

Prediction map TIFs are excluded from the repo (245 MB total). To regenerate:

```bash
# Train models — skips already-trained params automatically
python pipeline/03_train_models.py --combined --all-params --skip-done

# Generate Krishna District maps at 100 m (~3 min total)
python pipeline/05_predict_maps.py --combined --all-params --no-gpr --no-qrf --downsample 10 --krishna
```

Maps are saved to `data/processed/maps/` and served automatically by the backend.

For GPU training, use the included `colab_train.ipynb` on Google Colab (T4 GPU, ~15 min).

---

## Dashboard Features

**Officials / District Dashboard**
- Interactive satellite map (ESRI World Imagery) with soil choropleth overlay
- Zoom in/out with scroll wheel; hover sample points to see exact values
- Switch between all 10 soil parameters and confidence score layer
- KPI cards: district mean, confidence %, deficient pixel %
- Deficiency bar chart and confidence histogram per parameter

**Farmer Advisory Portal** (English / Telugu)
- Fertilizer recommendation engine (ICAR nutrient balance method)
- Yield prediction vs. district average and optimised potential
- Pest & disease alerts driven by live 7-day weather forecast (Open-Meteo)
- Weather-aware fertilizer timing to avoid nutrient runoff
- Crop suitability scoring for paddy, cotton, groundnut, red gram
- Profitability calculator with MSP-based revenue projections
- Irrigation scheduler, government schemes, crop calendar, carbon credit estimator

---

## API Reference

### GET /api/maps/{param}/stats
Summary statistics for a prediction map.

```bash
curl http://localhost:8000/api/maps/pH/stats?window=combined
```

### GET /api/maps/{param}/raster.png
RdYlGn-coloured RGBA PNG for frontend choropleth overlay.

```bash
curl "http://localhost:8000/api/maps/pH/raster.png?window=combined" -o pH_map.png
```

### POST /api/recommend
ICAR fertilizer recommendation for a field.

```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "crop": "paddy",
    "soil": {"pH": 6.8, "EC": 0.45, "OC": 0.52,
             "N": 210, "P": 14, "K": 145,
             "Fe": 3.2, "Zn": 0.3, "B": 0.8, "Cu": 0.25},
    "target_yield": 5.5,
    "area_acres": 2.5
  }'
```

### POST /api/suitability
Score and rank all 4 AP focus crops against provided soil values.

### GET /api/weather/timing
7-day rain forecast with fertilizer application risk per day.

### POST /api/sms
Bilingual English + Telugu fertilizer advisory SMS.

Full interactive docs: **http://localhost:8000/docs**

---

## ML Architecture

| Model | Role |
|-------|------|
| **CatBoost + MAPIE** `CrossConformalRegressor` | Primary — 90% coverage-guaranteed prediction intervals |
| **Gaussian Process Regressor** | Bayesian uncertainty, used during training CV only |
| **Quantile Random Forest** | Asymmetric interval fallback (3× GradientBoostingRegressor) |

Ensemble weighted by calibration error across spatial k-fold CV folds.

| Feature | Detail |
|---------|--------|
| **Conformal prediction** | MAPIE — mathematically guaranteed 90% coverage, not heuristic SDs |
| **Spatial k-fold CV** | KMeans clustering on lat/lon — prevents autocorrelation leakage |
| **Feature stack** | 40+ features: Sentinel-2 bands, spectral indices (BSI, clay, iron, NDRE, salinity), SRTM terrain (TWI, slope, curvature) |
| **ICAR nutrient balance** | `Dose = (Crop Req − Soil Supply) / FUE` — traceable to AP guidelines |
| **Telugu localisation** | Full UI and SMS output in Telugu |
| **COG output** | Cloud-Optimized GeoTIFF with LZW compression |

---

## Training Data

| Source | Rows |
|--------|------|
| Real Soil Health Cards (AP) | 299 |
| Synthetic augmentation | 5,000 |
| **Total** | **5,299** |

Synthetic data generated using spectral–soil correlations from real SHC samples and satellite feature distributions across Krishna District.

---

## Model Performance (Spatial CV)

| Param | RMSE | R² | Coverage |
|-------|------|----|----------|
| pH | 0.201 | 0.171 | ~90% |
| EC | 0.536 | 0.164 | ~90% |
| OC | 0.101 | 0.575 | ~90% |
| N | 39.4 | 0.301 | ~90% |
| Fe | 2.484 | 0.578 | ~90% |
| P, K, Cu, B, Zn | varies | low* | ~90% |

*Low R² for micronutrients is expected — sparse SHC coverage limits accuracy, but conformal intervals remain calibrated regardless.

---

## Pilot Area

- **District**: Krishna, Andhra Pradesh
- **Bounds**: 80.58–81.62°E, 15.65–16.82°N
- **Output resolution**: 100 m (downsample factor 10 from 10 m Sentinel-2)
- **Season**: Post-Kharif 2024 bare-soil composite (NDVI < 0.25 mask)
- **Crops**: Paddy, Cotton, Groundnut, Red Gram

---

*All ICAR values sourced from published guidelines for AP soils. Weather data from Open-Meteo (open-meteo.com). Satellite tiles from ESRI World Imagery.*
