"""
Module 1 — Feature Engineering
================================
Reads the raw GeoTIFFs downloaded by 01_data_ingest.py and produces a
single stacked feature GeoTIFF (EPSG:32644, 10 m) ready for ML training.

Steps:
  1. Reproject & resample all rasters to common grid (10 m, EPSG:32644)
  2. Clip to pilot AOI
  3. Stack Sentinel-2 bands + spectral indices + terrain features
  4. Write feature_stack.tif + feature_names.json to data/processed/

Usage:
    python pipeline/02_feature_engineering.py [--window post_kharif_2024]
"""

import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.warp import calculate_default_transform, reproject
from loguru import logger
from tqdm import tqdm

from config import (
    BARE_SOIL_WINDOWS,
    OUTPUT_RES,
    PILOT_BBOX,
    PROCESSED_DIR,
    RAW_DIR,
    TARGET_CRS,
    S2_BAND_NAMES,
    SPECTRAL_INDICES,
    TERRAIN_FEATURES,
    ALL_FEATURES,
)

# ---------------------------------------------------------------------------
# Raster utilities
# ---------------------------------------------------------------------------

def open_warped(src_path: Path, target_crs: str, resolution: int) -> WarpedVRT:
    """Open a raster as a virtual reprojection to target_crs and resolution."""
    src = rasterio.open(src_path)
    transform, width, height = calculate_default_transform(
        src.crs, target_crs, src.width, src.height, *src.bounds,
        resolution=resolution,
    )
    vrt_options = {
        "resampling": Resampling.bilinear,
        "crs": target_crs,
        "transform": transform,
        "width": width,
        "height": height,
    }
    return WarpedVRT(src, **vrt_options)


def read_band(vrt: WarpedVRT, band_idx: int = 1) -> np.ndarray:
    """Read a single band, returning float32 with NaN for nodata."""
    data = vrt.read(band_idx).astype(np.float32)
    nodata = vrt.nodata
    if nodata is not None:
        data[data == nodata] = np.nan
    return data


def align_to_reference(src_path: Path, ref_transform, ref_crs: str,
                        ref_shape: tuple[int, int]) -> np.ndarray:
    """Reproject src raster to match reference grid exactly (shape + transform)."""
    height, width = ref_shape
    with rasterio.open(src_path) as src:
        n_bands = src.count
        dest = np.full((n_bands, height, width), np.nan, dtype=np.float32)
        reproject(
            source=rasterio.band(src, list(range(1, n_bands + 1))),
            destination=dest,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=ref_transform,
            dst_crs=ref_crs,
            resampling=Resampling.bilinear,
        )
    return dest


# ---------------------------------------------------------------------------
# Locate raw files
# ---------------------------------------------------------------------------

def find_s2_file(window_label: str) -> Path | None:
    # Prefer the exact merged file (no tile coordinate suffix)
    merged = RAW_DIR / "sentinel2" / f"s2_baresoil_krishna_{window_label}.tif"
    if merged.exists():
        return merged
    # Fall back to any matching file (tiles)
    candidates = list((RAW_DIR / "sentinel2").glob(f"*{window_label}*.tif"))
    if not candidates:
        logger.warning(f"No Sentinel-2 file found for window: {window_label}")
        return None
    return candidates[0]


def find_terrain_file() -> Path | None:
    candidates = list((RAW_DIR / "dem").glob("terrain_*.tif"))
    if not candidates:
        logger.warning("No terrain file found in data/raw/dem/")
        return None
    return candidates[0]


# ---------------------------------------------------------------------------
# Planet data ingestion (if provided by hackathon organisers)
# ---------------------------------------------------------------------------

def load_planet_bands(ref_transform, ref_crs: str,
                      ref_shape: tuple[int, int]) -> np.ndarray | None:
    """
    Load Planet 3 m bare-soil composite if available, resample to 10 m grid.
    Planet files should be placed in data/raw/planet/ as GeoTIFFs.
    Returns array of shape (n_planet_bands, H, W) or None if absent.
    """
    planet_files = list((RAW_DIR / "planet").glob("*.tif"))
    if not planet_files:
        return None

    logger.info(f"Found {len(planet_files)} Planet file(s) — integrating…")
    arrays = []
    for pf in sorted(planet_files):
        arr = align_to_reference(pf, ref_transform, ref_crs, ref_shape)
        arrays.append(arr)
    return np.concatenate(arrays, axis=0)


# ---------------------------------------------------------------------------
# Normalisation / quality checks
# ---------------------------------------------------------------------------

def flag_invalid_pixels(stack: np.ndarray) -> np.ndarray:
    """
    Return a boolean mask (H, W): True = at least one band is NaN.
    Used downstream to exclude pixels from training.
    """
    return np.any(np.isnan(stack), axis=0)


def clip_extreme_values(arr: np.ndarray, lo: float = 0.01,
                         hi: float = 0.99) -> np.ndarray:
    """Winsorise at lo/hi percentile to suppress GEE edge artefacts."""
    valid = arr[~np.isnan(arr)]
    if valid.size == 0:
        return arr
    lo_val, hi_val = np.nanpercentile(arr, [lo * 100, hi * 100])
    return np.clip(arr, lo_val, hi_val)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

CHUNK_ROWS = 512  # process this many rows at a time to stay within RAM


def build_feature_stack(window_label: str):
    s2_path      = find_s2_file(window_label)
    terrain_path = find_terrain_file()

    if s2_path is None:
        raise FileNotFoundError(
            f"Sentinel-2 composite for '{window_label}' not found in data/raw/sentinel2/. "
            "Run 01_data_ingest.py first."
        )

    logger.info(f"Loading Sentinel-2 composite: {s2_path.name}")
    with rasterio.open(s2_path) as src:
        ref_transform = src.transform
        ref_crs       = src.crs.to_string()
        ref_shape     = (src.height, src.width)
        ref_profile   = src.profile.copy()
        n_s2_bands    = src.count
        nodata        = src.nodata
    logger.info(f"  Sentinel-2 shape: ({n_s2_bands}, {ref_shape[0]}, {ref_shape[1]})")

    # ── Terrain metadata ──────────────────────────────────────────────────────
    n_terrain = 0
    if terrain_path:
        with rasterio.open(terrain_path) as tsrc:
            n_terrain = tsrc.count
        logger.info(f"  Terrain bands: {n_terrain}")
    else:
        logger.warning("Terrain file missing — terrain features will be skipped.")

    n_planet = 0  # Planet handled separately if present

    # ── Build feature names ──────────────────────────────────────────────────
    gee_band_names = (S2_BAND_NAMES + SPECTRAL_INDICES)[:n_s2_bands]
    terrain_names  = TERRAIN_FEATURES[:n_terrain]
    feature_names  = gee_band_names + terrain_names
    logger.info(f"Total features: {len(feature_names)}")

    # ── Chunked write — one strip of CHUNK_ROWS at a time ────────────────────
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_tif    = PROCESSED_DIR / f"feature_stack_{window_label}.tif"
    names_json = PROCESSED_DIR / f"feature_names_{window_label}.json"
    n_total    = n_s2_bands + n_terrain
    H, W       = ref_shape

    out_profile = ref_profile.copy()
    out_profile.update({
        "driver": "GTiff", "dtype": "float32", "count": n_total,
        "compress": "LZW", "tiled": True,
        "blockxsize": 512, "blockysize": 512, "BIGTIFF": "YES",
    })

    logger.info(f"Writing feature stack (chunked) → {out_tif}")
    n_valid_pixels = 0
    n_total_pixels = 0

    with rasterio.open(s2_path) as s2_src, \
         (rasterio.open(terrain_path) if terrain_path else None) as t_src, \
         rasterio.open(out_tif, "w", **out_profile) as dst:

        n_chunks = (H + CHUNK_ROWS - 1) // CHUNK_ROWS
        for ci in tqdm(range(n_chunks), desc="Writing chunks"):
            row_start = ci * CHUNK_ROWS
            row_end   = min(row_start + CHUNK_ROWS, H)
            win       = rasterio.windows.Window(0, row_start, W, row_end - row_start)
            ch        = row_end - row_start

            # Read S2 chunk
            s2_chunk = s2_src.read(window=win).astype(np.float32)
            nd = s2_src.nodata
            if nd is not None:
                s2_chunk[s2_chunk == nd] = np.nan

            parts = [s2_chunk]

            # Reproject terrain chunk
            if t_src is not None:
                win_transform = s2_src.window_transform(win)
                t_chunk = np.full((n_terrain, ch, W), np.nan, dtype=np.float32)
                reproject(
                    source=rasterio.band(t_src, list(range(1, n_terrain + 1))),
                    destination=t_chunk,
                    src_transform=t_src.transform,
                    src_crs=t_src.crs,
                    dst_transform=win_transform,
                    dst_crs=s2_src.crs,
                    resampling=Resampling.bilinear,
                )
                parts.append(t_chunk)

            chunk = np.concatenate(parts, axis=0)  # (n_total, ch, W)

            # Track valid pixel coverage
            valid = ~np.any(np.isnan(chunk), axis=0)
            n_valid_pixels += int(valid.sum())
            n_total_pixels += ch * W

            dst.write(chunk, window=win)

    pct_valid = 100 * n_valid_pixels / max(n_total_pixels, 1)
    logger.info(f"Valid pixel coverage: {pct_valid:.1f}%")

    with open(names_json, "w") as f:
        json.dump({"window": window_label, "features": feature_names}, f, indent=2)

    logger.success(
        f"Feature stack saved: {out_tif}\n"
        f"  Bands: {n_total}  |  Shape: {H}×{W}\n"
        f"  Feature names: {names_json}"
    )
    return out_tif, feature_names


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build ML feature stack from raw rasters")
    parser.add_argument(
        "--window",
        default=BARE_SOIL_WINDOWS[0]["label"],
        choices=[w["label"] for w in BARE_SOIL_WINDOWS],
        help="Which bare-soil window to process (default: post_kharif_2024)",
    )
    parser.add_argument(
        "--all-windows", action="store_true",
        help="Process all configured bare-soil windows and stack temporally",
    )
    args = parser.parse_args()

    if args.all_windows:
        outputs = []
        for w in BARE_SOIL_WINDOWS:
            tif, names = build_feature_stack(w["label"])
            outputs.append((tif, names))
        logger.success(f"All windows processed: {[str(o[0]) for o in outputs]}")
    else:
        build_feature_stack(args.window)


if __name__ == "__main__":
    main()
