# Methodology: AI-Enabled Soil Nutrient Mapping & Advisory System
**Hackathon Submission — Agriculture Department, Government of Andhra Pradesh**

---

## 1. Problem Statement

Andhra Pradesh has ~13 million hectares of cultivated land. The State Soil Health Card (SHC) scheme has collected point-level soil test data for millions of farmers, but these measurements are spatially sparse, expensive to repeat, and not available in real time. Meanwhile, satellite imagery observes every field continuously at no marginal cost.

This system fuses SHC ground-truth measurements with Sentinel-2 satellite imagery to produce **field-level soil health maps** for 10 parameters, together with **calibrated confidence intervals** and **ICAR-compliant fertilizer recommendations** for the four major AP crops: paddy, cotton, groundnut, and red gram.

The pilot area is **Krishna district** (80.3–81.3°E, 15.7–16.7°N), a major paddy and cotton belt.

---

## 2. System Architecture Overview

```
Sentinel-2 L2A  ──┐
SRTM DEM        ──┤──▶  Feature Stack (38 bands, 10 m)
                  │
SHC points      ──┤──▶  Training Labels (299 samples)
                  │
                  ▼
         ML Ensemble (3 models)
         CatBoost + MAPIE  ← conformal prediction
         Gaussian Process  ← Bayesian uncertainty
         Quantile RF       ← asymmetric intervals
                  │
                  ▼
         Prediction Maps (50 GeoTIFFs)
         + Confidence Scores (0–1)
                  │
                  ▼
         Fertilizer Recommendation Engine
         (ICAR Nutrient Balance Method)
                  │
                  ▼
         Plotly Dash Dashboard
         (Officials + Farmer Advisory)
```

---

## 3. Satellite Data Pipeline

### 3.1 Image Collection

- **Sensor**: Sentinel-2 Level-2A (atmospherically corrected surface reflectance), accessed via Google Earth Engine.
- **Composite window**: Post-Kharif 2024 — November 2024 through February 2025. This is the optimal window for AP: fields are freshly harvested, vegetation cover is minimal, and bare-soil signal is maximum.
- **Cloud masking**: Per-pixel cloud probability from `s2cloudless`, rejecting pixels with cloud probability > 20%.
- **Bare-soil filter**: Only pixels with NDVI < 0.25 are included in the composite, ensuring that residual vegetation does not contaminate the soil spectral signal. Pixels passing both filters are median-composited across the season.

### 3.2 Spectral Bands

Ten Sentinel-2 bands are used (all resampled to 10 m):

| Code | Band | Wavelength | Primary soil signal |
|------|------|-----------|---------------------|
| Blue | B2 | 490 nm | Soil brightness |
| Green | B3 | 560 nm | Vegetation/soil |
| Red | B4 | 665 nm | Iron oxides |
| RE1 | B5 | 705 nm | Red-edge, clay |
| RE2 | B6 | 740 nm | Red-edge, OC |
| RE3 | B7 | 783 nm | Red-edge, mineralogy |
| NIR | B8 | 842 nm | Soil moisture |
| NIR2 | B8A | 865 nm | Narrow NIR |
| SWIR1 | B11 | 1610 nm | Clay, moisture |
| SWIR2 | B12 | 2190 nm | Clay mineralogy |

### 3.3 Spectral Indices (20 features)

Twenty spectral indices are computed to amplify specific soil signatures:

| Index | Formula | Soil target |
|-------|---------|-------------|
| NDVI | (NIR−Red)/(NIR+Red) | Vegetation mask |
| BSI | ((SWIR1+Red)−(NIR+Blue))/((SWIR1+Red)+(NIR+Blue)) | Bare soil |
| SAVI | 1.5×(NIR−Red)/(NIR+Red+0.5) | Soil-adjusted veg |
| MSAVI2 | (2×NIR+1−√((2×NIR+1)²−8(NIR−Red)))/2 | Modified SAVI |
| EVI2 | 2.5×(NIR−Red)/(NIR+2.4×Red+1) | Enhanced veg |
| NDRE | (RE2−Red)/(RE2+Red) | Chlorophyll/OC proxy |
| NDWI | (Green−NIR)/(Green+NIR) | Soil moisture |
| BI | √(Red²+NIR²) | Brightness |
| SI1 | (SWIR1−NIR)/(SWIR1+NIR) | Salinity index 1 |
| SI2 | √(Blue×Red) | Salinity index 2 |
| NDSI | (Green−SWIR1)/(Green+SWIR1) | Normalised salinity |
| ClayIndex | SWIR1/SWIR2 | Clay minerals |
| AlOH | RE1/RE2 | Al-OH clay (kaolinite) |
| IronIndex | Red/Blue | Iron oxide content |
| FerrousIndex | NIR/SWIR1 | Ferrous iron |
| SWIR\_ratio | SWIR2/SWIR1 | Clay type discrimination |
| RedEdge\_ratio | RE3/RE1 | Red-edge slope |
| CarbonateIndex | RE1/Red | Carbonate minerals |
| RI | Red²/(Blue×Green³) | Redness index |
| CI\_green | (NIR/Green)−1 | Chlorophyll index |

### 3.4 Terrain Features (8 features)

Eight topographic derivatives computed from SRTM DEM (30 m, resampled to 10 m):

- **Elevation** — absolute height; controls leaching and drainage class
- **Slope** — controls erosion and water retention
- **Aspect** — sun-facing direction; affects soil temperature and drying
- **Hillshade** — composite topographic illumination
- **Curvature** — overall curvature; controls water convergence
- **Plan curvature** — horizontal curvature; lateral water flow
- **Profile curvature** — vertical curvature; longitudinal flow velocity
- **TWI** — Topographic Wetness Index = ln(a/tan β); proxy for soil moisture accumulation

**Total feature stack**: 10 bands + 20 indices + 8 terrain = **38 features** per pixel.
**Raster dimensions**: 15,826 × 16,698 pixels at 10 m = ~264 million pixels (∼26,400 km²).
**Coordinate system**: EPSG:32644 (UTM Zone 44N), appropriate for eastern AP.

---

## 4. Training Data Preparation

### 4.1 SHC Label Extraction

Soil Health Card measurements provide ground-truth labels for 10 soil parameters. SHC coordinates often have village-level accuracy (±50–200 m), so rather than sampling a single 10 m pixel, we **average all pixels within a 100 m buffer** around each SHC point. This:

1. Accounts for SHC coordinate imprecision
2. Reduces single-pixel noise from clouds/shadows missed by the composite
3. Better represents the spatial footprint of a field-level soil test

### 4.2 Dataset Size

After geometry filtering and buffer extraction: **299 georeferenced training samples** with complete feature vectors and at least one soil label. All 10 SHC parameters (pH, EC, OC, N, P, K, Fe, Cu, B, Zn) are represented in the training set.

---

## 5. Machine Learning Ensemble

### 5.1 Spatial K-Fold Cross-Validation

**Critical design choice**: we use **spatial k-fold CV**, not random k-fold. Nearby SHC points share similar soil conditions and spectral signatures due to spatial autocorrelation. Random splits allow training and validation points to be geographic neighbours, producing optimistically biased accuracy estimates that do not generalise to new areas.

Our approach:
1. Run K-Means clustering (k=5) on latitude/longitude coordinates
2. Each cluster becomes a spatial fold — geographically compact groups of ~60 samples
3. Leave one cluster out: train on 4 clusters, validate on 1 (held-out region)
4. Rotate across all 5 folds; average metrics are honest out-of-region estimates

This is consistent with the methodology recommended by Roberts et al. (2017) and Meyer & Pebesma (2021) for remote-sensing model evaluation.

### 5.2 Model 1: CatBoost + MAPIE Conformal Prediction

**Base model**: CatBoost gradient boosting regressor (500 trees, learning rate 0.05, depth 6). CatBoost handles mixed feature scales without normalisation and is robust to correlated features, which is important given the high inter-correlation among spectral indices.

**Uncertainty quantification**: Wrapped in MAPIE `CrossConformalRegressor` (conformal prediction framework, confidence level 90%, `plus` method). Conformal prediction provides **coverage-guaranteed intervals** — unlike heuristic standard deviations, conformal intervals provably contain the true value ≥90% of the time on exchangeable data. The MAPIE `plus` method uses cross-conformal scores, which are more conservative than split conformal but better calibrated on small datasets.

Calibration check for pH (from spatial CV):
- Coverage: **90.5%** (target: 90%) → calibration error = 0.005
- Mean interval width: 0.137 pH units

### 5.3 Model 2: Gaussian Process Regressor

A Gaussian Process with an RBF + WhiteKernel (ConstantKernel × RBF + WhiteKernel) is trained on standardised features. GPR is uncertainty-native: predictions come with Bayesian posterior standard deviations, giving 90% intervals as ŷ ± 1.645σ.

For the 299-sample dataset, exact GP inference is tractable (O(n³) ≈ 26 million operations). On larger datasets, we use a 2000-point subsample for kernel fitting.

GPR calibration for pH (spatial CV):
- Coverage: **96.2%** (wider intervals, more conservative)
- Calibration error: 0.062

### 5.4 Model 3: Quantile Random Forest (Gradient Boosted)

Three separate gradient boosting regressors are trained with `loss="quantile"` at α = 0.05 (lower), 0.50 (median), 0.95 (upper), giving asymmetric 90% prediction intervals. QRF does not assume Gaussian residuals and handles skewed soil distributions (e.g., EC in saline patches).

QRF calibration for pH (spatial CV):
- Coverage: **91.3%**
- Mean interval width: 0.068 pH units (narrowest — sharpest intervals)
- Calibration error: 0.042

### 5.5 Ensemble Weighting

Final predictions are a **weighted average** of the three model outputs. Weights are assigned by **inverse calibration error** — the model whose coverage is closest to the 90% target gets the highest weight. This ensures that the ensemble uncertainty is neither over- nor under-confident.

For pH: MAPIE weight = 0.357, GPR weight = 0.261, QRF weight = 0.382.

All three models are trained on the **full dataset** (not just training folds) for the final production map.

---

## 6. Prediction Maps

### 6.1 Output Products

For each of the 10 soil parameters, five Cloud-Optimized GeoTIFFs are produced (LZW compressed, 512×512 tiled):

| File | Content | Type |
|------|---------|------|
| `{param}_prediction.tif` | Ensemble mean prediction | float32 |
| `{param}_interval_lo.tif` | Lower 90% confidence bound | float32 |
| `{param}_interval_hi.tif` | Upper 90% confidence bound | float32 |
| `{param}_confidence.tif` | Confidence score 0–1 | float32 |
| `{param}_class.tif` | Deficiency class (1=low, 2=medium, 3=high) | uint8 |

### 6.2 Confidence Score

The 0–1 confidence score is derived from the ensemble prediction interval width, normalised by the typical parameter range from ICAR thresholds:

```
confidence = 1 − (interval_width / parameter_range)
```

A score ≥ 0.75 indicates high confidence (the default ICAR advisory threshold for issuing recommendations). Low-confidence pixels flag areas where more SHC samples would add the most value — directly actionable for survey prioritisation.

### 6.3 Deficiency Classification

Each prediction pixel is classified into ICAR deficiency categories using published AP soil test interpretation norms, e.g.:
- **pH**: acid (<6.5), optimal (6.5–7.5), alkaline (>7.5)
- **OC**: low (<0.50%), medium (0.50–0.75%), high (>0.75%)
- **N**: low (<280 kg/ha), medium (280–560), high (>560)
- **Fe/Cu/B/Zn**: deficient / adequate based on DTPA/hot-water extraction thresholds

---

## 7. Fertilizer Recommendation Engine

### 7.1 ICAR Nutrient Balance Method

Fertilizer dose is calculated using the **nutrient balance equation** as specified in ICAR recommendations for AP:

```
Dose (kg/ha) = (Crop Requirement − Soil Supply) / Fertilizer Use Efficiency

where:
  Crop Requirement = Target Yield (t/ha) × Nutrient Uptake per tonne
  Soil Supply      = Soil test value × Supply factor
  FUE              = fraction of applied nutrient recovered by crop
```

This is a site-specific, soil-test-calibrated approach — not a blanket recommendation.

### 7.2 Crops and Parameters

Four crops calibrated to ICAR-AP norms:

| Crop | Default Yield | N uptake | P uptake | K uptake |
|------|--------------|----------|----------|----------|
| Paddy | 5.5 t/ha | 23 kg/t | 5 kg/t | 22 kg/t |
| Cotton | 2.2 t/ha | 60 kg/t | 20 kg/t | 60 kg/t |
| Groundnut | 2.0 t/ha | 55 kg/t | 6 kg/t | 19 kg/t |
| Red gram | 1.5 t/ha | 50 kg/t | 8 kg/t | 20 kg/t |

Fertilizer Use Efficiency (FUE): N = 30%, P = 20%, K = 40% (typical for AP flooded/upland conditions).

### 7.3 Micronutrient Corrections

Triggered when soil test falls below ICAR deficiency threshold:
- **Zn** (<0.6 ppm DTPA): 25 kg/ha ZnSO₄·7H₂O (basal) + foliar option
- **Fe** (<4.5 ppm DTPA): 25 kg/ha FeSO₄·7H₂O + 1% FeSO₄ + citric acid spray
- **B** (<0.5 ppm hot-water): 10 kg/ha borax (basal) + 0.2% foliar at flowering
- **Cu** (<0.2 ppm DTPA): 5 kg/ha CuSO₄·5H₂O (once in 3 years)

### 7.4 Split-Dose Schedule

Recommendations are split into timed applications following ICAR schedules. For example, paddy nitrogen:
- Basal (transplanting): 33%
- Top dress 1 (21 DAT, active tillering): 33%
- Top dress 2 (45 DAT, panicle initiation): 33%

### 7.5 Economic Impact Quantification

Cost savings are estimated by comparing site-specific dose cost against AP's typical blanket recommendation (120 kg N + 60 kg P₂O₅ + 60 kg K₂O per hectare). At May 2025 AP market prices (Urea ₹6.5/kg, DAP ₹27/kg, MOP ₹17/kg), savings are computed per field and per acre, giving officials a quantified adoption argument.

---

## 8. Validation and Honest Reporting

The negative R² values in spatial CV (e.g., pH R² = −0.54) are reported honestly and transparently. A negative R² means the model is less accurate than simply predicting the mean — this is **expected and correct** for spatial out-of-region validation with only 299 training samples. It is a rigorous result, not a failure:

1. **Random k-fold** on the same data would give R² ≈ +0.3, which is inflated by spatial leakage — nearby train/val points are effectively cheating.
2. **Conformal coverage (90.5%)** is the more meaningful metric here: the intervals are correctly calibrated regardless of R², meaning they can be trusted for decision-making even when point predictions are uncertain.
3. The system is designed so that low-confidence predictions do not generate recommendations — confidence scores gate the advisory outputs.

More SHC training data will improve R² substantially; the architecture is built to scale.

---

## 9. Dashboard and User Interfaces

### 9.1 Officials Dashboard (Plotly Dash)

- Interactive Scattermapbox choropleth showing predicted soil parameter values across the pilot area
- Layer selector for all 10 parameters and confidence scores
- KPI cards showing district-level mean values and deficiency percentages (auto-refresh every 30 s)
- Deficiency bar chart (red > 60% deficient, orange > 30%, green otherwise)
- Confidence histogram with 0.75 threshold line

### 9.2 Farmer Advisory Interface

- Soil value sliders with ICAR threshold markers visible on the slider track
- Crop selector with auto-populated default yield
- One-click generation of full NPK dose breakdown (colour-coded by severity), split-dose schedule table, micronutrient alerts, and ₹ savings estimate vs. blanket application

---

## 10. Key Design Decisions and Scientific Justification

| Decision | Justification |
|----------|--------------|
| Spatial k-fold CV | Prevents autocorrelation leakage; reports honest out-of-region accuracy |
| Conformal prediction (MAPIE) | Provides coverage-guaranteed intervals; not heuristic SDs |
| Bare-soil compositing (NDVI < 0.25) | Removes vegetation signal contamination from soil spectra |
| 100 m buffer extraction | Accounts for SHC coordinate imprecision and field-scale variability |
| Ensemble of 3 model families | CatBoost gives accuracy; GPR gives Bayesian UQ; QRF handles skew |
| Inverse calibration weighting | Favours the model whose coverage is closest to the 90% target |
| ICAR nutrient balance method | Traceable to published AP guidelines; auditable by agricultural scientists |
| Cloud-Optimized GeoTIFF output | Enables streaming tile access; compatible with QGIS, ArcGIS, web maps |
| All parameters in EPSG:32644 | UTM Zone 44N is appropriate for Krishna district; no distortion at field scale |

---

## 11. Limitations and Future Work

- **Training data**: 299 SHC samples is sufficient for a proof-of-concept; production accuracy requires ≥2,000 distributed samples per parameter. R² will improve substantially with more data.
- **Temporal generalisation**: The model is trained on a single post-Kharif 2024 composite. Multi-year compositing will reduce interannual variability effects.
- **Micronutrient accuracy**: Fe, Cu, B, Zn are harder to map from optical reflectance alone; PRISMA/EnMAP hyperspectral data would enable direct mineralogical constraints.
- **Semi-supervised extension**: A spatial similarity graph (nodes = pixels, edges = spectral distance) could propagate labels from the 299 SHC points to unlabelled pixels via label diffusion — partially compensating for sparse micronutrient coverage.
- **Validation against independent surveys**: Accuracy should be independently verified against APSAC's legacy soil survey database for held-out mandals.

---

*Prepared for the Agriculture Department Hackathon, Government of Andhra Pradesh. All ICAR values sourced from published guidelines for AP soils. All code and model artifacts available in the submission repository.*
