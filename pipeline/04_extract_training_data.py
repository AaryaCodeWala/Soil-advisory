"""
Module 1.5 — Extract Training Data
====================================
Joins georeferenced SHC points to the feature stack raster.
For each SHC point extracts the mean pixel values within a 100 m buffer
(matching satellite resolution and the spatial imprecision of field sampling).

Outputs:
  data/processed/training_data_{window}.csv  — X features + y labels
  data/processed/training_data_{window}.gpkg — same with geometry

Usage:
    python pipeline/04_extract_training_data.py [--window post_kharif_2024]
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask as rio_mask
from shapely.geometry import mapping
from loguru import logger
from tqdm import tqdm

from config import (
    BARE_SOIL_WINDOWS,
    PROCESSED_DIR,
    SOIL_PARAMS,
    TARGET_CRS,
)

BUFFER_METERS = 100   # SHC village-level accuracy; average over 100 m radius


def load_shc(path: Path) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    # Keep only points with valid geometry
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    logger.info(f"SHC points with geometry: {len(gdf):,}")
    return gdf


def reproject_shc(gdf: gpd.GeoDataFrame, target_crs: str) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return gdf.to_crs(target_crs)


def extract_buffer_mean(
    src: rasterio.DatasetReader,
    geom,
    buffer_m: float = BUFFER_METERS,
) -> np.ndarray | None:
    """
    Extract the mean pixel value within a circular buffer around a point.
    Returns array of shape (n_bands,) or None if no valid pixels.
    """
    buffered = geom.buffer(buffer_m)
    try:
        data, _ = rio_mask(src, [mapping(buffered)], crop=True, nodata=np.nan, filled=True)
        # data shape: (bands, rows, cols)
        data = data.astype(np.float32)
        if src.nodata is not None:
            data[data == src.nodata] = np.nan
        flat = data.reshape(data.shape[0], -1)
        if flat.size == 0 or np.all(np.isnan(flat)):
            return None
        return np.nanmean(flat, axis=1)
    except Exception:
        return None


def read_feature_names(window_label: str) -> list[str]:
    names_json = PROCESSED_DIR / f"feature_names_{window_label}.json"
    if names_json.exists():
        with open(names_json) as f:
            return json.load(f)["features"]
    # Fallback: read band tag names from the raster
    tif = PROCESSED_DIR / f"feature_stack_{window_label}.tif"
    with rasterio.open(tif) as src:
        names = []
        for i in range(1, src.count + 1):
            tag = src.tags(i).get("name", f"band_{i}")
            names.append(tag)
    return names


def extract_features(window_label: str, shc_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    stack_path = PROCESSED_DIR / f"feature_stack_{window_label}.tif"
    if not stack_path.exists():
        raise FileNotFoundError(
            f"{stack_path} not found. Run 02_feature_engineering.py first."
        )

    feature_names = read_feature_names(window_label)
    logger.info(f"Extracting {len(feature_names)} features at {len(shc_gdf):,} SHC points…")

    rows = []
    with rasterio.open(stack_path) as src:
        # Ensure SHC points are in same CRS as raster
        if shc_gdf.crs.to_string() != src.crs.to_string():
            shc_gdf = shc_gdf.to_crs(src.crs.to_string())

        raster_bounds = src.bounds
        for idx, row in tqdm(shc_gdf.iterrows(), total=len(shc_gdf), desc="Extracting"):
            geom = row.geometry
            # Skip points outside raster extent
            if not (raster_bounds.left <= geom.x <= raster_bounds.right and
                    raster_bounds.bottom <= geom.y <= raster_bounds.top):
                continue

            means = extract_buffer_mean(src, geom)
            if means is None:
                continue

            record = {name: val for name, val in zip(feature_names, means)}

            # Attach soil labels (SHC GeoPackage stores estimates as est_<param>)
            for param in SOIL_PARAMS:
                est_col = f"est_{param}"
                if est_col in row.index:
                    record[f"label_{param}"] = row[est_col]

            # Attach metadata
            for col in ["farmer_id", "village", "mandal", "district", "sample_date"]:
                if col in row.index:
                    record[col] = row[col]

            record["geometry_wkt"] = geom.wkt
            record["lat"] = shc_gdf.to_crs("EPSG:4326").iloc[
                shc_gdf.index.get_loc(idx)
            ].geometry.y if shc_gdf.crs.to_epsg() != 4326 else geom.y
            record["lon"] = shc_gdf.to_crs("EPSG:4326").iloc[
                shc_gdf.index.get_loc(idx)
            ].geometry.x if shc_gdf.crs.to_epsg() != 4326 else geom.x

            rows.append(record)

    df = pd.DataFrame(rows)
    logger.info(f"Extracted {len(df):,} training samples with features.")
    return df


def quality_report(df: pd.DataFrame):
    label_cols = [c for c in df.columns if c.startswith("label_")]
    logger.info("\n── Training data quality ───────────────────────────────────")
    for col in label_cols:
        param = col.replace("label_", "")
        n     = df[col].notna().sum()
        logger.info(f"  {param:4s}: {n:5d} labelled samples")


def main():
    parser = argparse.ArgumentParser(description="Extract pixel features at SHC point locations")
    parser.add_argument(
        "--window",
        default=BARE_SOIL_WINDOWS[0]["label"],
        choices=[w["label"] for w in BARE_SOIL_WINDOWS],
    )
    args = parser.parse_args()

    shc_path = PROCESSED_DIR / "shc_processed.gpkg"
    if not shc_path.exists():
        logger.error(
            "shc_processed.gpkg not found. Run 03_shc_processing.py first."
        )
        return

    shc_gdf = load_shc(shc_path)
    shc_gdf = reproject_shc(shc_gdf, TARGET_CRS)

    df = extract_features(args.window, shc_gdf)
    quality_report(df)

    # Save outputs
    out_csv  = PROCESSED_DIR / f"training_data_{args.window}.csv"
    out_gpkg = PROCESSED_DIR / f"training_data_{args.window}.gpkg"

    df.drop(columns=["geometry_wkt"], errors="ignore").to_csv(out_csv, index=False)
    logger.success(f"Training CSV → {out_csv}  ({len(df):,} rows)")

    gdf_out = gpd.GeoDataFrame(
        df,
        geometry=gpd.GeoSeries.from_wkt(df["geometry_wkt"]),
        crs=TARGET_CRS,
    )
    gdf_out.to_file(out_gpkg, driver="GPKG")
    logger.success(f"Training GeoPackage → {out_gpkg}")


if __name__ == "__main__":
    main()
