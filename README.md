# AI-Enabled Soil Nutrient Mapping & Advisory System
**Agriculture Department, Government of Andhra Pradesh — Hackathon Submission**

Field-level soil health maps for Krishna District with calibrated confidence intervals and ICAR-compliant fertilizer recommendations for paddy, cotton, groundnut, and red gram.

---

## Quick Start (2 minutes)

### Option A — Docker Compose (recommended)

```bash
# Clone and enter the repo
git clone <repo-url> && cd soil-advisory

# Start API + dashboard (pre-generated maps are in data/processed/maps/)
docker compose up api dashboard
```

- Dashboard: http://localhost:8050
- API docs:   http://localhost:8000/docs

### Option B — Local Python

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/Mac

pip install -r requirements.txt

# Dashboard
python dashboard/app.py

# API (separate terminal)
uvicorn backend.main:app --reload --port 8000
```

---

## What the System Produces

| Output | Description |
|--------|-------------|
| **10 soil parameter maps** | pH, EC, OC, N, P, K, Fe, Cu, B, Zn — full Krishna District at 10 m |
| **Confidence intervals** | 90% prediction intervals per pixel (conformal-guaranteed) |
| **Confidence scores** | 0–1 score gating advisory outputs |
| **Deficiency class maps** | ICAR-classified low/medium/high per pixel |
| **Fertilizer advisory** | ICAR nutrient balance method, 4 crops, site-specific doses |
| **Bilingual SMS** | English + Telugu, segment-counted, feature-phone ready |

---

## Repository Layout

```
soil-advisory/
├── pipeline/
│   ├── config.py                  # AOI, CRS, parameter list
│   ├── 01_data_ingest.py          # GEE Sentinel-2 download
│   ├── 02_feature_engineering.py  # 38-band feature stack (S2 + terrain)
│   ├── 03_shc_processing.py       # Soil Health Card georeferencing
│   ├── 03_train_models.py         # CatBoost+MAPIE, GP, Quantile RF
│   ├── 04_extract_training_data.py# SHC → feature vector alignment
│   ├── 05_predict_maps.py         # Pixel-level inference → GeoTIFFs
│   ├── fertilizer_tables.py       # All ICAR crop/nutrient tables
│   └── sms_formatter.py           # Bilingual SMS generation
├── backend/
│   ├── main.py                    # FastAPI app
│   └── routers/
│       ├── maps.py                # GET /api/maps/{param}
│       ├── recommendations.py     # POST /api/recommend
│       └── sms.py                 # POST /api/sms
├── dashboard/
│   └── app.py                     # Plotly Dash — officials + farmer tabs
├── gee/                           # Google Earth Engine scripts
├── docs/
│   └── methodology.md             # Full scientific writeup (11 sections)
├── data/
│   └── processed/maps/            # 50 prediction GeoTIFFs (pre-generated)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Running the Full Pipeline (optional — maps already pre-generated)

```bash
# 1. Download Sentinel-2 composite from GEE
python pipeline/01_data_ingest.py --window post_kharif_2024

# 2. Build 38-band feature stack
python pipeline/02_feature_engineering.py --window post_kharif_2024

# 3. Process Soil Health Card data
python pipeline/03_shc_processing.py

# 4. Extract training features at SHC locations
python pipeline/04_extract_training_data.py --window post_kharif_2024

# 5. Train ensemble models
python pipeline/03_train_models.py --window post_kharif_2024 --all-params

# 6. Generate prediction maps for all 10 parameters
python pipeline/05_predict_maps.py --window post_kharif_2024 --all-params
```

Or with Docker (GPU-friendly):
```bash
docker compose --profile predict up predict
```

---

## API Reference

### POST /api/recommend
Generate ICAR fertilizer recommendation for a field.

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

### POST /api/sms
Generate bilingual SMS advisory (English + Telugu).

```bash
curl -X POST http://localhost:8000/api/sms \
  -H "Content-Type: application/json" \
  -d '{
    "crop": "paddy",
    "soil": {"pH": 6.8, "N": 210, "P": 14, "K": 145, "Zn": 0.3, "Fe": 3.2},
    "area_acres": 2.5,
    "farmer_name": "Ravi Reddy",
    "lang": "both",
    "mode": "short"
  }'
```

### GET /api/maps/{param}
Sample predicted values + confidence scores as JSON points.

Full interactive docs: **http://localhost:8000/docs**

---

## Dashboard

Open **http://localhost:8050** and use the two tabs:

**Officials Tab**
- Select any of the 10 soil parameters from the dropdown
- Toggle between predicted value and confidence score layers
- KPI cards show district-level means and % deficient fields
- Deficiency bar chart highlights which parameters need most attention

**Farmer Advisory Tab**
- Select crop and enter field area
- Adjust soil test sliders (or type values from SHC)
- Toggle English / Telugu using the language switch
- Click "Generate Recommendation" for full NPK schedule, micronutrient corrections, and estimated cost savings vs. blanket application

---

## Technical Highlights

| Feature | Implementation |
|---------|---------------|
| **Conformal prediction** | MAPIE `CrossConformalRegressor` — 90% coverage-guaranteed intervals, not heuristic SDs |
| **Spatial k-fold CV** | 5-fold clustering on lat/lon — prevents spatial autocorrelation leakage |
| **3-model ensemble** | CatBoost (accuracy) + GP (Bayesian UQ) + Quantile RF (asymmetric intervals), weighted by calibration error |
| **38-feature stack** | 10 S2 bands + 20 spectral indices (BSI, clay index, iron index, NDRE, salinity) + 8 SRTM terrain derivatives |
| **ICAR nutrient balance** | `Dose = (Crop Req − Soil Supply) / FUE` — traceable to published AP guidelines |
| **Telugu localisation** | Full UI in Telugu throughout farmer advisory and SMS |
| **COG output** | Cloud-Optimized GeoTIFF with LZW compression, 512×512 tiles |
| **EPSG:32644** | UTM Zone 44N for all internal processing; EPSG:4326 at API boundaries only |

---

## Pilot Area

- **District**: Krishna, Andhra Pradesh
- **Extent**: 80.3–81.3°E, 15.7–16.7°N (~26,400 km²)
- **Raster size**: 15,826 × 16,698 pixels at 10 m resolution
- **Training samples**: 299 georeferenced SHC points
- **Season**: Post-Kharif 2024 (Nov 2024 – Feb 2025 bare-soil composite)

---

## Methodology

See [`docs/methodology.md`](docs/methodology.md) for the full scientific writeup covering:
- Bare-soil compositing and NDVI < 0.25 filtering
- All 20 spectral indices with soil-science justification
- Conformal prediction calibration results (90.5% coverage for pH)
- Honest reporting of negative R² from spatial CV and why it is expected
- ICAR nutrient balance equations with crop-specific FUE values
- Economic impact quantification methodology

---

*All ICAR values sourced from published guidelines for AP soils. Code and model artifacts in this repository.*
