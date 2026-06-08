"""
Synthetic training data generator for Krishna District soil nutrient mapping.

Generates realistic Sentinel-2 spectral features + terrain features + soil labels
using empirical distributions from actual SHC data and physically-grounded
spectral-soil relationships for Andhra Pradesh conditions.

Output: data/processed/synthetic_training_data.csv  (~5000 rows)
        data/processed/combined_training_data.csv   (real + synthetic)
"""

import numpy as np
import pandas as pd
from pathlib import Path

RNG = np.random.default_rng(42)

# Krishna district bounding box (EPSG:4326)
LAT_MIN, LAT_MAX = 15.85, 16.80
LON_MIN, LON_MAX = 80.20, 81.35

N_SYNTHETIC = 5000

# ---------------------------------------------------------------------------
# Spatial clusters — simulate mandal-level soil variation
# ---------------------------------------------------------------------------
MANDAL_CENTERS = [
    (16.52, 80.62),  # Vijayawada rural
    (16.43, 80.52),  # Gannavaram
    (16.35, 81.08),  # Gudlavalleru
    (16.10, 80.90),  # Challapalli
    (16.05, 81.10),  # Avanigadda
    (16.55, 81.00),  # Ghantasala
    (16.25, 80.45),  # Bapulapadu
    (16.70, 80.75),  # Ibrahimpatnam
    (16.30, 80.70),  # Kankipadu
    (16.45, 81.20),  # Bantumilli
    (16.00, 80.65),  # Nagayalanka
    (16.60, 80.40),  # Penamaluru
]

def sample_locations(n):
    """Sample lat/lon with spatial clustering around mandal centers."""
    centers = np.array(MANDAL_CENTERS)
    chosen = centers[RNG.integers(0, len(centers), size=n)]
    # Add cluster spread ~0.08° (~8 km radius)
    lat = np.clip(chosen[:, 0] + RNG.normal(0, 0.08, n), LAT_MIN, LAT_MAX)
    lon = np.clip(chosen[:, 1] + RNG.normal(0, 0.08, n), LON_MIN, LON_MAX)
    return lat, lon


# ---------------------------------------------------------------------------
# Terrain features — derived from SRTM for Krishna district
# Mostly flat deltaic plain; some upland areas in NW
# ---------------------------------------------------------------------------
def generate_terrain(lat, lon, n):
    # Upland fraction increases west/northwest
    upland_score = np.clip((16.6 - lat) * 0.3 + (80.6 - lon) * 0.5, 0, 1)
    upland = RNG.random(n) < upland_score * 0.25  # ~25% max upland

    elevation = np.where(upland,
                         RNG.uniform(20, 120, n),
                         RNG.uniform(2, 25, n))
    slope = np.where(upland,
                     RNG.gamma(2, 1.5, n),
                     RNG.gamma(1, 0.5, n))
    aspect = RNG.uniform(0, 360, n)
    hillshade = 180 + RNG.normal(0, 5, n) - slope * 0.3
    hillshade = np.clip(hillshade, 100, 255)
    curvature = RNG.normal(0, 0.8, n)
    plan_curv = RNG.normal(0, 4, n)
    prof_curv = RNG.normal(0, 1.0, n)
    # TWI: flat = high TWI
    twi = np.where(upland,
                   RNG.normal(1.2, 0.4, n),
                   RNG.normal(1.8, 0.4, n))
    return dict(elevation=elevation, slope=slope, aspect=aspect,
                hillshade=hillshade, curvature=curvature,
                plan_curvature=plan_curv, profile_curvature=prof_curv,
                TWI=twi), upland


# ---------------------------------------------------------------------------
# Soil labels — sample from calibrated distributions
# Correlations:
#   - High clay → lower OC drainage, higher CEC (K retention)
#   - Saline areas → higher EC, slightly higher pH
#   - Upland → lower pH (more leaching), lower K
#   - OC correlated with N (organic N pool)
# ---------------------------------------------------------------------------
def generate_soil_labels(n, upland, lat, lon):
    # pH: mostly neutral 6.9-7.4; saline patches up to 8.5
    saline = RNG.random(n) < 0.12
    ph_base = np.where(saline,
                       RNG.normal(7.6, 0.3, n),
                       RNG.normal(7.05, 0.12, n))
    ph_base = np.where(upland, ph_base - RNG.uniform(0, 0.3, n), ph_base)
    pH = np.clip(ph_base, 6.4, 8.8)

    # EC (dS/m)
    EC = np.where(saline,
                  RNG.gamma(3, 0.5, n) + 0.4,
                  np.where(RNG.random(n) < 0.08,
                           RNG.uniform(0.8, 2.5, n),
                           RNG.choice([0.4], n) + RNG.exponential(0.05, n)))
    EC = np.clip(EC, 0.1, 4.0)

    # OC (%) — predominantly low in AP (0.25-0.75), rarely >1
    oc_mean = 0.55 + RNG.normal(0, 0.05, n)
    oc_mean -= 0.05 * saline.astype(float)  # saline soils slightly lower OC
    OC = np.clip(RNG.normal(oc_mean, 0.15, n), 0.25, 1.5)

    # N (kg/ha) — strongly tied to OC; low overall
    N = np.clip(OC * 280 + RNG.normal(0, 30, n), 100, 500)

    # P (kg/ha)
    P = np.clip(RNG.gamma(3.5, 5, n) + 5, 2, 45)

    # K (kg/ha) — bimodal: low (55) vs medium (150-300)
    low_k = RNG.random(n) < 0.55
    K = np.where(low_k,
                 55 + RNG.exponential(20, n),
                 RNG.uniform(100, 420, n))
    K = np.clip(K, 30, 500)

    # Fe (mg/kg) — ~50% deficient (<4.5 ppm)
    Fe_deficient = RNG.random(n) < 0.50
    Fe = np.where(Fe_deficient,
                  RNG.uniform(2.0, 4.5, n),
                  RNG.uniform(4.5, 15.0, n))
    Fe = np.clip(Fe, 1.5, 20.0)

    # Cu (mg/kg) — mostly sufficient (>0.2)
    Cu = np.clip(RNG.beta(5, 2, n) * 0.85 + 0.05, 0.05, 1.2)

    # B (mg/kg) — ~60% deficient (<0.5)
    B_deficient = RNG.random(n) < 0.60
    B = np.where(B_deficient,
                 RNG.uniform(0.20, 0.50, n),
                 RNG.uniform(0.50, 2.0, n))
    B = np.clip(B, 0.10, 2.5)

    # Zn (mg/kg) — wide range, ~40% deficient (<0.6)
    Zn_deficient = RNG.random(n) < 0.40
    Zn = np.where(Zn_deficient,
                  RNG.uniform(0.20, 0.60, n),
                  RNG.uniform(0.60, 2.5, n))
    Zn = np.clip(Zn, 0.10, 3.0)

    return dict(label_pH=pH, label_EC=EC, label_OC=OC, label_N=N,
                label_P=P, label_K=K, label_Fe=Fe, label_Cu=Cu,
                label_B=B, label_Zn=Zn), saline


# ---------------------------------------------------------------------------
# Spectral features — physically-grounded bare-soil reflectance model
# Based on relationships from Sentinel-2 bare-soil composites over AP
# ---------------------------------------------------------------------------
def generate_spectral(n, soil, saline, upland):
    OC  = soil["label_OC"]
    Fe  = soil["label_Fe"]
    Clay = RNG.beta(4, 3, n) * 0.6 + 0.1   # clay fraction proxy (not measured)
    EC   = soil["label_EC"]

    # Base soil brightness increases with sand, decreases with OC
    brightness = 0.25 + (1 - OC) * 0.15 - Clay * 0.06 + RNG.normal(0, 0.02, n)

    # Band reflectances for bare soil (Sentinel-2)
    Blue  = np.clip(brightness * 0.38 + saline * 0.02 + RNG.normal(0, 0.01, n), 0.02, 0.55)
    Green = np.clip(brightness * 0.50 + RNG.normal(0, 0.01, n), 0.03, 0.60)
    Red   = np.clip(brightness * 0.60 - OC * 0.05 + Fe * 0.005 + RNG.normal(0, 0.015, n), 0.03, 0.65)
    RE1   = np.clip(Red * 1.05 + RNG.normal(0, 0.008, n), 0.04, 0.68)
    RE2   = np.clip(Red * 1.18 + RNG.normal(0, 0.008, n), 0.05, 0.72)
    RE3   = np.clip(Red * 1.30 + RNG.normal(0, 0.008, n), 0.06, 0.75)
    NIR   = np.clip(brightness * 0.72 - OC * 0.04 + RNG.normal(0, 0.015, n), 0.08, 0.80)
    NIR2  = np.clip(NIR * 1.04 + RNG.normal(0, 0.010, n), 0.08, 0.82)
    SWIR1 = np.clip(brightness * 0.90 + Clay * 0.08 + RNG.normal(0, 0.018, n), 0.05, 0.90)
    SWIR2 = np.clip(brightness * 0.70 + Clay * 0.05 - OC * 0.03 + RNG.normal(0, 0.015, n), 0.03, 0.80)

    # Derived spectral indices
    NDVI  = (NIR - Red) / (NIR + Red + 1e-9)
    BSI   = ((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue) + 1e-9)
    SAVI  = 1.5 * (NIR - Red) / (NIR + Red + 0.5)
    MSAVI2 = (2 * NIR + 1 - np.sqrt((2 * NIR + 1)**2 - 8 * (NIR - Red))) / 2
    EVI2  = 2.5 * (NIR - Red) / (NIR + 2.4 * Red + 1 + 1e-9)
    NDRE  = (RE2 - RE1) / (RE2 + RE1 + 1e-9)
    NDWI  = (Green - NIR) / (Green + NIR + 1e-9)
    BI    = np.sqrt((Red**2 + Green**2 + NIR**2) / 3)
    SI1   = (Green + Red) / 2
    SI2   = np.sqrt(Green * Red)
    NDSI  = (Green - SWIR1) / (Green + SWIR1 + 1e-9)
    ClayIndex = SWIR1 / SWIR2
    AlOH  = ClayIndex.copy()
    IronIndex = Red / Green
    FerrousIndex = NIR / SWIR1
    SWIR_ratio = SWIR1 / SWIR2
    RedEdge_ratio = RE1 / Red * 50   # scale like original
    CarbonateIndex = RE1 / Green
    RI    = Red / Green
    CI_green = NIR / Green - 1

    return dict(Blue=Blue, Green=Green, Red=Red, RE1=RE1, RE2=RE2, RE3=RE3,
                NIR=NIR, NIR2=NIR2, SWIR1=SWIR1, SWIR2=SWIR2,
                NDVI=NDVI, BSI=BSI, SAVI=SAVI, MSAVI2=MSAVI2, EVI2=EVI2,
                NDRE=NDRE, NDWI=NDWI, BI=BI, SI1=SI1, SI2=SI2, NDSI=NDSI,
                ClayIndex=ClayIndex, AlOH=AlOH, IronIndex=IronIndex,
                FerrousIndex=FerrousIndex, SWIR_ratio=SWIR_ratio,
                RedEdge_ratio=RedEdge_ratio, CarbonateIndex=CarbonateIndex,
                RI=RI, CI_green=CI_green)


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------
def generate(n=N_SYNTHETIC):
    print(f"Generating {n} synthetic samples...")
    lat, lon = sample_locations(n)
    terrain, upland = generate_terrain(lat, lon, n)
    soil, saline = generate_soil_labels(n, upland, lat, lon)
    spectral = generate_spectral(n, soil, saline, upland)

    df = pd.DataFrame({**spectral, **terrain,
                       **soil, "lat": lat, "lon": lon})

    # Column order to match real training data
    column_order = [
        "Blue","Green","Red","RE1","RE2","RE3","NIR","NIR2","SWIR1","SWIR2",
        "NDVI","BSI","SAVI","MSAVI2","EVI2","NDRE","NDWI","BI","SI1","SI2",
        "NDSI","ClayIndex","AlOH","IronIndex","FerrousIndex","SWIR_ratio",
        "RedEdge_ratio","CarbonateIndex","RI","CI_green",
        "elevation","slope","aspect","hillshade","curvature",
        "plan_curvature","profile_curvature","TWI",
        "label_pH","label_EC","label_OC","label_N","label_P","label_K",
        "label_Fe","label_Cu","label_B","label_Zn","lat","lon",
    ]
    df = df[column_order]
    return df


def main():
    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    synth = generate(N_SYNTHETIC)

    synth_path = out_dir / "synthetic_training_data.csv"
    synth.to_csv(synth_path, index=False)
    print(f"Saved {len(synth)} synthetic rows to {synth_path}")

    # Combine with real data
    real_path = out_dir / "training_data_post_kharif_2024.csv"
    if real_path.exists():
        real = pd.read_csv(real_path)
        real["source"] = "real"
        synth_tagged = synth.copy()
        synth_tagged["source"] = "synthetic"
        combined = pd.concat([real, synth_tagged], ignore_index=True)
        combined_path = out_dir / "combined_training_data.csv"
        combined.to_csv(combined_path, index=False)
        print(f"Saved combined ({len(real)} real + {len(synth)} synthetic) to {combined_path}")

    # Quick stats comparison
    print("\n--- Synthetic label distributions ---")
    label_cols = ["label_pH","label_EC","label_OC","label_N",
                  "label_P","label_K","label_Fe","label_Cu","label_B","label_Zn"]
    print(synth[label_cols].describe().to_string())

    if real_path.exists():
        print("\n--- Real label distributions ---")
        print(real[label_cols].describe().to_string())


if __name__ == "__main__":
    main()
