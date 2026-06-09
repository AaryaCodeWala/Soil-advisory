"""
Module 1.5 — Soil Health Card (SHC) Data Processing
=====================================================
Cleans, validates, and georeferencing the SHC CSV provided by the hackathon.
Outputs a GeoParquet file of georeferenced training points.

Expected input CSV columns (flexible — will auto-detect):
  farmer_id, village, mandal, district, latitude, longitude,
  pH, EC, OC, N, P, K, Fe, Cu, B, Zn, S, sample_date

Usage:
    python pipeline/03_shc_processing.py --input data/raw/shc/shc_data.csv
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from loguru import logger

from config import PROCESSED_DIR, RAW_DIR, SOIL_PARAMS

# ---------------------------------------------------------------------------
# Column name aliases — map common variants to canonical names
# ---------------------------------------------------------------------------

COLUMN_ALIASES = {
    # Identifiers
    "farmer_id":   ["farmer_id", "FarmerID", "farmer id", "id"],
    "village":     ["village", "Village", "village_name", "VillageName"],
    "mandal":      ["mandal", "Mandal", "taluk", "block"],
    "district":    ["district", "District"],
    "sample_date": ["sample_date", "SampleDate", "date", "Date", "collection_date"],

    # Coordinates
    "latitude":    ["latitude", "Latitude", "lat", "Lat", "GPS_Lat"],
    "longitude":   ["longitude", "Longitude", "lon", "Long", "lng", "GPS_Long"],

    # Soil parameters
    "pH":  ["pH", "ph", "PH", "soil_ph"],
    "EC":  ["EC", "ec", "electrical_conductivity", "EC_dSm"],
    "OC":  ["OC", "oc", "organic_carbon", "OrganicCarbon", "OC_percent"],
    "N":   ["N", "nitrogen", "available_n", "Nitrogen", "AN"],
    "P":   ["P", "phosphorus", "available_p", "Phosphorus", "AP", "P2O5"],
    "K":   ["K", "potassium", "available_k", "Potassium", "AK", "K2O"],
    "Fe":  ["Fe", "iron", "Iron", "DTPA_Fe"],
    "Cu":  ["Cu", "copper", "Copper", "DTPA_Cu"],
    "B":   ["B", "boron", "Boron", "HWB"],
    "Zn":  ["Zn", "zinc", "Zinc", "DTPA_Zn"],
    "S":   ["S", "sulphur", "sulfur", "Sulphur", "available_s"],
}

# ---------------------------------------------------------------------------
# Valid ranges for soil parameters (domain knowledge filter)
# ---------------------------------------------------------------------------

VALID_RANGES = {
    "pH":  (3.0,  10.0),
    "EC":  (0.0,  20.0),   # dS/m
    "OC":  (0.0,   5.0),   # %
    "N":   (0.0, 1500.0),  # kg/ha
    "P":   (0.0,  200.0),  # kg/ha
    "K":   (0.0,  800.0),  # kg/ha
    "Fe":  (0.0,  100.0),  # ppm
    "Cu":  (0.0,   20.0),  # ppm
    "B":   (0.0,   10.0),  # ppm
    "Zn":  (0.0,   20.0),  # ppm
    "S":   (0.0,  100.0),  # ppm
}

# Andhra Pradesh bounding box for coordinate validation
AP_LAT_RANGE = (12.5, 20.0)
AP_LON_RANGE = (76.5, 85.0)

# ---------------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------------

def detect_columns(df: pd.DataFrame) -> dict[str, str]:
    """Map canonical names to actual DataFrame column names."""
    cols_lower = {c.lower().strip(): c for c in df.columns}
    mapping    = {}

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias.lower() in cols_lower:
                mapping[canonical] = cols_lower[alias.lower()]
                break

    found   = list(mapping.keys())
    missing = [c for c in COLUMN_ALIASES if c not in mapping]
    logger.info(f"Detected columns: {found}")
    if missing:
        logger.warning(f"Missing columns: {missing}")
    return mapping


# ---------------------------------------------------------------------------
# Cleaning functions
# ---------------------------------------------------------------------------

def standardise_columns(df: pd.DataFrame, col_map: dict[str, str]) -> pd.DataFrame:
    """Rename detected columns to canonical names."""
    rename = {v: k for k, v in col_map.items()}
    return df.rename(columns=rename)


def clean_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce soil parameter columns to numeric, replace invalid with NaN."""
    params = [p for p in SOIL_PARAMS if p in df.columns]
    for col in params:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def remove_out_of_range(df: pd.DataFrame) -> pd.DataFrame:
    """Replace values outside physically valid ranges with NaN."""
    before = len(df)
    for param, (lo, hi) in VALID_RANGES.items():
        if param not in df.columns:
            continue
        mask = (df[param] < lo) | (df[param] > hi)
        df.loc[mask, param] = np.nan

    nulls = df[list(VALID_RANGES.keys())].isnull().sum().sum()
    logger.info(f"Out-of-range values replaced with NaN: {nulls}")
    return df


def remove_iqr_outliers(df: pd.DataFrame, k: float = 3.0) -> pd.DataFrame:
    """Winsorise extreme outliers using IQR × k rule per parameter."""
    for param in SOIL_PARAMS:
        if param not in df.columns:
            continue
        q1, q3 = df[param].quantile(0.25), df[param].quantile(0.75)
        iqr     = q3 - q1
        lo, hi  = q1 - k * iqr, q3 + k * iqr
        n_out   = ((df[param] < lo) | (df[param] > hi)).sum()
        df.loc[df[param] < lo, param] = np.nan
        df.loc[df[param] > hi, param] = np.nan
        if n_out:
            logger.debug(f"  {param}: {n_out} IQR outliers → NaN")
    return df


def filter_stale_samples(df: pd.DataFrame, max_age_years: int = 2) -> pd.DataFrame:
    """Drop SHC samples older than max_age_years (stale readings not reliable)."""
    if "sample_date" not in df.columns:
        logger.warning("No sample_date column — keeping all records.")
        return df

    df["sample_date"] = pd.to_datetime(df["sample_date"], errors="coerce", dayfirst=True)
    cutoff = datetime.now() - timedelta(days=max_age_years * 365)
    before = len(df)
    df = df[df["sample_date"].isna() | (df["sample_date"] >= cutoff)]
    logger.info(f"Stale sample filter: {before - len(df)} records dropped (>{max_age_years} yrs old)")
    return df


# ---------------------------------------------------------------------------
# Georeferencing
# ---------------------------------------------------------------------------

def validate_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """Flag rows with missing or out-of-AP coordinates."""
    if "latitude" not in df.columns or "longitude" not in df.columns:
        df["latitude"]  = np.nan
        df["longitude"] = np.nan
        return df

    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Zero coordinates are almost always missing/placeholder values
    df.loc[df["latitude"]  == 0, "latitude"]  = np.nan
    df.loc[df["longitude"] == 0, "longitude"] = np.nan

    # Out-of-AP coordinates
    out_of_ap = (
        (df["latitude"]  < AP_LAT_RANGE[0]) | (df["latitude"]  > AP_LAT_RANGE[1]) |
        (df["longitude"] < AP_LON_RANGE[0]) | (df["longitude"] > AP_LON_RANGE[1])
    )
    df.loc[out_of_ap, ["latitude", "longitude"]] = np.nan
    logger.info(f"Invalid/out-of-AP coordinates set to NaN: {out_of_ap.sum()}")
    return df


def build_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Create GeoDataFrame from lat/lon columns.
    Rows without coordinates are kept but have null geometry
    (useful for semi-supervised learning later).
    """
    has_coords = df["latitude"].notna() & df["longitude"].notna()
    geometry   = [
        Point(lon, lat) if valid else None
        for valid, lat, lon in zip(has_coords, df["latitude"], df["longitude"])
    ]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    logger.info(
        f"Georeferenced: {has_coords.sum()} points with coordinates, "
        f"{(~has_coords).sum()} without."
    )
    return gdf


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def print_summary(gdf: gpd.GeoDataFrame):
    params_present = [p for p in SOIL_PARAMS if p in gdf.columns]
    logger.info("\n── Soil parameter summary ──────────────────────────────────")
    for param in params_present:
        s = gdf[param].dropna()
        if len(s) == 0:
            continue
        logger.info(
            f"  {param:4s}: n={len(s):5d}  "
            f"mean={s.mean():7.3f}  "
            f"std={s.std():6.3f}  "
            f"[{s.min():.3f} – {s.max():.3f}]"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_shc(input_path: Path, max_age_years: int = 2) -> gpd.GeoDataFrame:
    logger.info(f"Loading SHC data: {input_path}")
    df = pd.read_csv(input_path, low_memory=False)
    logger.info(f"  Raw records: {len(df):,}  |  Columns: {list(df.columns)}")

    col_map = detect_columns(df)
    df      = standardise_columns(df, col_map)
    df      = clean_numeric(df)
    df      = remove_out_of_range(df)
    df      = remove_iqr_outliers(df)
    df      = filter_stale_samples(df, max_age_years)
    df      = validate_coordinates(df)
    gdf     = build_geodataframe(df)

    print_summary(gdf)

    # Drop rows with no soil parameter data at all
    params_present = [p for p in SOIL_PARAMS if p in gdf.columns]
    has_any = gdf[params_present].notna().any(axis=1)
    gdf = gdf[has_any].reset_index(drop=True)
    logger.info(f"Final records: {len(gdf):,}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "shc_processed.gpkg"
    gdf.to_file(out_path, driver="GPKG")
    logger.success(f"Saved → {out_path}")
    return gdf


def main():
    parser = argparse.ArgumentParser(description="Clean and georeference SHC data")
    parser.add_argument(
        "--input", type=Path,
        default=RAW_DIR / "shc" / "shc_data.csv",
        help="Path to raw SHC CSV file",
    )
    parser.add_argument(
        "--max-age", type=int, default=2,
        help="Maximum SHC sample age in years (default: 2)",
    )
    args = parser.parse_args()

    if not args.input.exists():
        logger.error(
            f"SHC file not found: {args.input}\n"
            "Place the hackathon-provided CSV at data/raw/shc/shc_data.csv"
        )
        return

    process_shc(args.input, args.max_age)


if __name__ == "__main__":
    main()
