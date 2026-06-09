"""
Module 1.5 — SHC Aggregate Data Processor (Village-Level Percentages)
======================================================================
Merges all Nutrient*.csv files (one per mandal), converts percentage
distributions to estimated mean values per village using class midpoints,
geocodes village names via OpenStreetMap Nominatim, and outputs a
GeoPackage ready for feature extraction.

Class midpoint method:
  estimated_mean = sum(pct_class_i * midpoint_i) / 100

Usage:
    python pipeline/03_shc_processing_aggregate.py
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from loguru import logger

from config import PROCESSED_DIR, RAW_DIR

SHC_DIR = RAW_DIR / "shc"

# ---------------------------------------------------------------------------
# Class midpoints for converting % distributions → estimated mean values
# (ICAR classification ranges for AP soils)
# ---------------------------------------------------------------------------

MIDPOINTS = {
    "N":  {"Low": 140.0,  "Medium": 420.0, "High": 700.0},
    "P":  {"Low": 5.5,    "Medium": 16.5,  "High": 33.0},
    "K":  {"Low": 55.0,   "Medium": 195.0, "High": 420.0},
    "OC": {"Low": 0.25,   "Medium": 0.625, "High": 1.0},
    "pH": {"Acidic": 5.5, "Neutral": 7.0,  "Alkaline": 8.25},
    "EC": {"Non Saline": 0.4, "Saline": 3.0},
    "S":  {"Deficient": 5.0,  "Sufficient": 20.0},
    "Fe": {"Deficient": 2.25, "Sufficient": 12.0},
    "Zn": {"Deficient": 0.3,  "Sufficient": 1.5},
    "Cu": {"Deficient": 0.1,  "Sufficient": 0.8},
    "B":  {"Deficient": 0.25, "Sufficient": 1.5},
    "Mn": {"Deficient": 1.0,  "Sufficient": 8.0},
}

# Column name mappings in the CSV
PARAM_COLS = {
    "N":  [("N_High", "High"),   ("N_Medium", "Medium"), ("N_Low", "Low")],
    "P":  [("P_High", "High"),   ("P_Medium", "Medium"), ("P_Low", "Low")],
    "K":  [("K_High", "High"),   ("K_Medium", "Medium"), ("K_Low", "Low")],
    "OC": [("OC_High", "High"),  ("OC_Medium", "Medium"), ("OC_Low", "Low")],
    "pH": [("P H_Alkaline", "Alkaline"), ("P H_Acidic", "Acidic"), ("P H_Neutral", "Neutral")],
    "EC": [("EC_Non Saline", "Non Saline"), ("EC_Saline", "Saline")],
    "S":  [("S_Sufficient", "Sufficient"), ("S_Deficient", "Deficient")],
    "Fe": [("Fe_Sufficient", "Sufficient"), ("Fe_Deficient", "Deficient")],
    "Zn": [("Zn_Sufficient", "Sufficient"), ("Zn_Deficient", "Deficient")],
    "Cu": [("Cu_Sufficient", "Sufficient"), ("Cu_Deficient", "Deficient")],
    "B":  [("B_Sufficient", "Sufficient"),  ("B_Deficient", "Deficient")],
    "Mn": [("Mn_Sufficient", "Sufficient"), ("Mn_Deficient", "Deficient")],
}

# ---------------------------------------------------------------------------
# Load and merge all CSVs
# ---------------------------------------------------------------------------

def load_all_csvs() -> pd.DataFrame:
    files = sorted(SHC_DIR.glob("Nutrient*.csv"))
    if not files:
        raise FileNotFoundError(f"No Nutrient*.csv files found in {SHC_DIR}")

    logger.info(f"Found {len(files)} CSV files")
    frames = []
    for f in files:
        try:
            # First line is metadata ("Cycle: 2025-26..."), skip it
            df = pd.read_csv(f, skiprows=1)
            frames.append(df)
        except Exception as e:
            logger.warning(f"  Could not read {f.name}: {e}")

    combined = pd.concat(frames, ignore_index=True)
    # Drop duplicate village+block combinations
    before = len(combined)
    combined = combined.drop_duplicates(subset=["Village", "Block"])
    logger.info(f"Loaded {before} rows → {len(combined)} unique village records")
    return combined


# ---------------------------------------------------------------------------
# Convert percentages → estimated mean values
# ---------------------------------------------------------------------------

def pct_to_mean(row: pd.Series, param: str) -> float:
    """Weighted mean using class midpoints."""
    total, weighted = 0.0, 0.0
    for col, class_name in PARAM_COLS[param]:
        if col not in row.index:
            continue
        try:
            pct = float(row[col])
        except (ValueError, TypeError):
            continue
        midpoint = MIDPOINTS[param][class_name]
        weighted += pct * midpoint
        total    += pct
    if total < 1.0:
        return np.nan
    return weighted / total


def estimate_values(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Converting percentage distributions to estimated values...")
    for param in MIDPOINTS:
        df[f"est_{param}"] = df.apply(lambda r: pct_to_mean(r, param), axis=1)
        valid = df[f"est_{param}"].notna().sum()
        logger.info(f"  {param}: {valid} villages with estimates")
    return df


# ---------------------------------------------------------------------------
# Geocoding via OpenStreetMap Nominatim
# ---------------------------------------------------------------------------

def geocode_village(village: str, mandal: str, district: str = "Krishna",
                    state: str = "Andhra Pradesh") -> tuple[float, float] | tuple[None, None]:
    """Query Nominatim for village coordinates. Returns (lat, lon) or (None, None)."""
    import urllib.request, urllib.parse, json

    queries = [
        f"{village}, {mandal}, {district}, {state}, India",
        f"{village}, {district}, {state}, India",
        f"{village}, {state}, India",
    ]
    headers = {"User-Agent": "SoilHackathon/1.0 (hackathon research project)"}

    for query in queries:
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
            "q": query, "format": "json", "limit": 1,
            "countrycodes": "in",
        })
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                results = json.loads(resp.read())
            if results:
                return float(results[0]["lat"]), float(results[0]["lon"])
        except Exception:
            pass
        time.sleep(1.1)  # Nominatim rate limit: 1 req/sec

    return None, None


def geocode_all(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Geocoding {len(df)} villages via OpenStreetMap Nominatim...")
    logger.info("  (Rate limited to 1 req/sec — this takes ~10 minutes for 400 villages)")

    lats, lons = [], []
    for i, row in df.iterrows():
        # Extract mandal name (format: "MANDAL_NAME - 5101")
        mandal_clean = str(row.get("Block", "")).split(" - ")[0].title()
        lat, lon = geocode_village(str(row["Village"]), mandal_clean)
        lats.append(lat)
        lons.append(lon)

        if (i + 1) % 20 == 0:
            geocoded = sum(x is not None for x in lats)
            logger.info(f"  Progress: {i+1}/{len(df)} | Geocoded: {geocoded}")

    df["latitude"]  = lats
    df["longitude"] = lons
    geocoded_count = df["latitude"].notna().sum()
    logger.info(f"Geocoded {geocoded_count}/{len(df)} villages ({geocoded_count/len(df):.0%})")
    return df


def build_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    has_coords = df["latitude"].notna() & df["longitude"].notna()
    geometry = [
        Point(lon, lat) if ok else None
        for ok, lat, lon in zip(has_coords, df["latitude"], df["longitude"])
    ]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    logger.info(f"GeoDataFrame: {has_coords.sum()} georeferenced, {(~has_coords).sum()} without coords")
    return gdf


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    df = load_all_csvs()
    df = estimate_values(df)

    # Print summary of estimated values
    logger.info("\n── Estimated soil values (district summary) ────────────────")
    for param in MIDPOINTS:
        col = f"est_{param}"
        if col in df.columns:
            s = df[col].dropna()
            if len(s):
                logger.info(f"  {param:4s}: mean={s.mean():.3f}  std={s.std():.3f}  "
                           f"[{s.min():.3f}–{s.max():.3f}]  n={len(s)}")

    df = geocode_all(df)
    gdf = build_geodataframe(df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / "shc_processed.gpkg"
    gdf.to_file(out, driver="GPKG")
    logger.success(f"Saved {len(gdf)} village records → {out}")

    # Also save as CSV for inspection
    csv_out = PROCESSED_DIR / "shc_processed.csv"
    gdf.drop(columns=["geometry"]).to_csv(csv_out, index=False)
    logger.success(f"CSV copy → {csv_out}")


if __name__ == "__main__":
    main()
