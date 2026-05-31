from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = DATA_DIR / "models"

# Coordinate reference system: UTM Zone 44N covers eastern AP (78-84°E)
TARGET_CRS = "EPSG:32644"
TARGET_CRS_EPSG = 32644

# Native resolutions (metres)
SENTINEL2_RES = 10
PLANET_RES = 3
OUTPUT_RES = 10  # resample everything to Sentinel-2 native

# Andhra Pradesh bounding box (WGS84)
AP_BBOX = {"west": 76.7, "east": 84.8, "south": 12.6, "north": 19.9}

# Pilot district: Krishna (major paddy/cotton belt, ~80-81°E clearly in Zone 44N)
PILOT_DISTRICT = "Krishna"
PILOT_BBOX = {"west": 80.30, "east": 81.30, "south": 15.70, "north": 16.70}

# Bare-soil composite windows: post-Kharif is best (fields cleared, no crops)
BARE_SOIL_WINDOWS = [
    {"start": "2024-11-01", "end": "2025-02-28", "label": "post_kharif_2024"},
    {"start": "2024-03-15", "end": "2024-06-15", "label": "pre_monsoon_2024"},
]

# Sentinel-2 bare-soil filter: pixels with NDVI below this threshold
BARE_SOIL_NDVI_MAX = 0.25

# Maximum cloud probability accepted per pixel (Sentinel-2 s2cloudless)
CLOUD_PROB_MAX = 20

# Soil parameters modelled (matches ICAR / SHC categories)
SOIL_PARAMS = ["pH", "EC", "OC", "N", "P", "K", "Fe", "Cu", "B", "Zn"]

# Sentinel-2 band names in GEE (SR, scale 0.0001)
S2_BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
S2_BAND_NAMES = ["Blue", "Green", "Red", "RE1", "RE2", "RE3", "NIR", "NIR2", "SWIR1", "SWIR2"]

# Spectral index names produced by feature engineering
SPECTRAL_INDICES = [
    "NDVI", "BSI", "SAVI", "MSAVI2", "EVI2",
    "NDRE", "NDWI", "BI",
    "SI1", "SI2", "NDSI",
    "ClayIndex", "AlOH", "IronIndex", "FerrousIndex",
    "SWIR_ratio", "RedEdge_ratio", "CarbonateIndex",
    "RI", "CI_green",
]

# Terrain feature names derived from SRTM DEM
TERRAIN_FEATURES = [
    "elevation", "slope", "aspect",
    "hillshade", "curvature", "plan_curvature", "profile_curvature",
    "TWI", "TRI", "TPI",
]

# All feature names in order (used to build model feature matrix)
ALL_FEATURES = S2_BAND_NAMES + SPECTRAL_INDICES + TERRAIN_FEATURES

# Focus crops
CROPS = ["paddy", "cotton", "groundnut", "red_gram"]

# Confidence score above which a prediction is considered "high confidence"
HIGH_CONFIDENCE_THRESHOLD = 0.75

# Google Drive folder where GEE exports land
GEE_DRIVE_FOLDER = "SoilHackathon_GEE"
GEE_PROJECT = "galvanic-idiom-464908-p9"
