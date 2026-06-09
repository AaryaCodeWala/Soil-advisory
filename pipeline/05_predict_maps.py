"""
Module 3 — Predict Soil Maps
=============================
Loads trained models and runs inference on the full feature stack raster,
producing per-parameter GeoTIFFs with:
  - predicted value
  - lower 90% confidence interval
  - upper 90% confidence interval
  - confidence score (0–1)

Outputs (data/processed/maps/):
  {param}_prediction.tif      — predicted value (float32)
  {param}_confidence.tif      — confidence score 0–1 (float32)
  {param}_interval_lo.tif     — lower bound (float32)
  {param}_interval_hi.tif     — upper bound (float32)
  {param}_class.tif           — deficiency class (uint8: 1=low,2=medium,3=high)

Usage:
    python pipeline/05_predict_maps.py [--param pH] [--all-params]
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
import joblib
from loguru import logger
from tqdm import tqdm

from config import (
    BARE_SOIL_WINDOWS,
    MODELS_DIR,
    PROCESSED_DIR,
    SOIL_PARAMS,
    HIGH_CONFIDENCE_THRESHOLD,
)
from fertilizer_tables import SOIL_THRESHOLDS

MAPS_DIR = PROCESSED_DIR / "maps"
CHUNK_SIZE = 1024  # process raster in chunks to avoid OOM


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def find_model_files(param: str, window: str) -> dict:
    """Find best model artifacts for a parameter.

    Prefers stems that have all three model types (mapie+gpr+qrf).
    Among ties, picks the highest R² (parsed from filename, not Path.stem
    which strips decimal extensions incorrectly).
    """
    pattern = f"{param}_{window}_*"
    files   = list(MODELS_DIR.glob(pattern))
    if not files:
        return {}

    def r2_from_stem(s: str) -> float:
        # Parse R² directly from the string — avoid Path.stem which strips
        # the decimal part (e.g. "_r2-0.543" → Path.stem gives "-0", not "-0.543")
        try:
            return float(s.split("_r2")[1].split("_")[0])
        except Exception:
            return -99.0

    stems = set(f.stem.rsplit("_", 1)[0] for f in files)

    # Prefer stems that have a mapie.pkl (complete runs with conformal intervals)
    stems_with_mapie = {s for s in stems if (MODELS_DIR / f"{s}_mapie.pkl").exists()}
    candidates = stems_with_mapie if stems_with_mapie else stems

    best_stem = max(candidates, key=r2_from_stem)

    result = {}
    for suffix in ["mapie", "gpr", "qrf", "meta"]:
        p = MODELS_DIR / f"{best_stem}_{suffix}.{'json' if suffix == 'meta' else 'pkl'}"
        if p.exists():
            result[suffix] = p
    return result


def load_models(model_files: dict) -> dict:
    models = {}
    for key in ["mapie", "gpr", "qrf"]:
        if key in model_files:
            try:
                models[key] = joblib.load(model_files[key])
                logger.debug(f"  Loaded {key}")
            except Exception as e:
                logger.warning(f"  Could not load {key}: {e}")

    # Precompute MAPIE conformity quantile so inference only needs one CatBoost
    # forward pass (base estimator) instead of K passes (predict_interval CV+).
    if "mapie" in models:
        try:
            mapie_obj = models["mapie"]
            scores = getattr(mapie_obj, "conformity_scores_",
                             getattr(getattr(mapie_obj, "_mapie_regressor", None),
                                     "conformity_scores_", None))
            q = float(np.quantile(np.abs(scores), 0.9)) if scores is not None else None
            models["mapie_q90"] = q
            logger.debug(f"  MAPIE conformity q90={q:.4f}")
        except Exception:
            models["mapie_q90"] = None

    if "meta" in model_files:
        with open(model_files["meta"]) as f:
            models["meta"] = json.load(f)
    return models


# ---------------------------------------------------------------------------
# Confidence score
# ---------------------------------------------------------------------------

PARAM_TYPICAL_RANGE = {
    "pH":  6.0,    # 4.0 – 10.0  practical AP soil range
    "EC":  4.0,    # 0.0 –  4.0  normal to highly saline
    "OC":  2.5,    # 0.0 –  2.5  %
    "N":   560.0,  # 0   – 560   kg/ha (low–high threshold span)
    "P":   50.0,   # 0   –  50   kg/ha
    "K":   400.0,  # 0   – 400   kg/ha
    "Fe":  20.0,   # 0   –  20   ppm DTPA
    "Cu":  2.0,    # 0   –   2   ppm DTPA
    "B":   3.0,    # 0   –   3   ppm hot-water
    "Zn":  3.0,    # 0   –   3   ppm DTPA
    "S":   50.0,   # 0   –  50   ppm
}

def interval_to_confidence(lo: np.ndarray, hi: np.ndarray, param: str) -> np.ndarray:
    """
    Normalise interval width to a 0–1 confidence score.
    Narrow interval relative to typical AP soil range → high confidence.
    Uses agronomically meaningful ranges, NOT ICAR threshold sentinels (which
    use 99.0 as 'no upper limit' and would make every score ~100%).
    """
    param_range = PARAM_TYPICAL_RANGE.get(param, None)
    if param_range is None:
        param_range = float(np.nanpercentile(hi - lo, 95)) * 10
    param_range = max(param_range, 1e-6)
    width      = np.clip(hi - lo, 0, param_range)
    confidence = 1.0 - (width / param_range)
    return np.clip(confidence, 0.0, 1.0).astype(np.float32)


# ---------------------------------------------------------------------------
# Deficiency classification
# ---------------------------------------------------------------------------

def classify(values: np.ndarray, param: str) -> np.ndarray:
    """
    Map continuous predictions to deficiency class integers.
    1 = low/deficient, 2 = medium/marginal, 3 = high/adequate
    """
    thresholds = SOIL_THRESHOLDS.get(param, {})
    out        = np.full(values.shape, 2, dtype=np.uint8)  # default: medium

    if param == "pH":
        out[values < 6.5] = 1   # acid
        out[values > 7.5] = 3   # alkaline
    elif param in ["Fe", "Cu", "B", "Zn"]:
        thr = list(thresholds.get("deficient", (0, 0)))[1]
        out[values < thr] = 1
        out[values >= thr] = 3
    else:
        items = list(thresholds.items())
        if len(items) >= 3:
            out[values < items[0][1][1]] = 1
            out[values >= items[1][1][1]] = 3
    return out


# ---------------------------------------------------------------------------
# Chunk-based raster prediction
# ---------------------------------------------------------------------------

def _clip_to_training_bounds(data: np.ndarray, window_label: str) -> np.ndarray:
    """Clip each band of data to its training-data min/max.

    CatBoost (and all tree models) extrapolate to leaf extremes outside the
    training distribution, producing constant predictions.  Clamping to
    training bounds keeps inference within the fitted range.
    """
    train_csv = PROCESSED_DIR / f"training_data_{window_label}.csv"
    names_json = PROCESSED_DIR / f"feature_names_{window_label}.json"
    if not train_csv.exists() or not names_json.exists():
        return data

    with open(names_json) as f:
        feature_names = json.load(f)["features"]

    df = pd.read_csv(train_csv)
    feat_cols = [c for c in feature_names if c in df.columns]
    if len(feat_cols) != data.shape[0]:
        logger.warning(f"Feature count mismatch: stack={data.shape[0]}, training={len(feat_cols)}")
        return data

    feat_min = df[feat_cols].min().values.astype(np.float32)
    feat_max = df[feat_cols].max().values.astype(np.float32)
    for b in range(data.shape[0]):
        np.clip(data[b], feat_min[b], feat_max[b], out=data[b])
    logger.info("  Feature bands clipped to training-data bounds.")
    return data


KRISHNA_BOUNDS_LATLON = (80.58, 15.65, 81.62, 16.82)  # (minlon, minlat, maxlon, maxlat)


def _crop_window(stack_path: Path, minlon: float, minlat: float,
                 maxlon: float, maxlat: float) -> rasterio.windows.Window | None:
    """Return rasterio Window for the given lat/lon bounding box, or None if full extent."""
    from rasterio.crs import CRS
    from rasterio.warp import transform_bounds
    with rasterio.open(stack_path) as src:
        src_crs = src.crs
        bounds  = transform_bounds("EPSG:4326", src_crs, minlon, minlat, maxlon, maxlat)
        win = src.window(*bounds)
        # Clamp to valid pixel range
        win = win.intersection(rasterio.windows.Window(0, 0, src.width, src.height))
    return win


def _load_stack_strided(stack_path: Path, ds: int,
                        crop_win: "rasterio.windows.Window | None" = None) -> np.ndarray:
    """Read feature stack at full resolution in 512-row strips then stride-sample.

    crop_win: if provided, only reads pixels inside that rasterio Window.
    GDAL silently converts float32 NaN → 0 when doing downsampled reads on
    LZW-compressed files without a declared nodata value.  Reading at full
    resolution and stride-sampling in numpy avoids that bug entirely.
    """
    with rasterio.open(stack_path) as src:
        if crop_win is not None:
            col_off = int(crop_win.col_off)
            row_off = int(crop_win.row_off)
            W       = int(crop_win.width)
            H       = int(crop_win.height)
        else:
            col_off, row_off = 0, 0
            H, W = src.height, src.width
        n_bands = src.count
        nodata  = src.nodata

    H_out    = (H + ds - 1) // ds
    W_out    = (W + ds - 1) // ds
    data_out = np.full((n_bands, H_out, W_out), np.nan, dtype=np.float32)

    IN_CHUNK = 512
    n_chunks = (H + IN_CHUNK - 1) // IN_CHUNK

    with rasterio.open(stack_path) as src:
        for ci in tqdm(range(n_chunks), desc="Loading stack (full-res strips)"):
            row_start = ci * IN_CHUNK
            row_end   = min(row_start + IN_CHUNK, H)
            win       = rasterio.windows.Window(col_off, row_off + row_start, W, row_end - row_start)

            chunk = src.read(window=win).astype(np.float32)
            if nodata is not None:
                chunk[chunk == nodata] = np.nan

            global_rows   = np.arange(row_start, row_end)
            local_sampled = np.where(global_rows % ds == 0)[0]
            if len(local_sampled) == 0:
                continue
            out_rows = global_rows[local_sampled] // ds

            sampled = chunk[:, local_sampled, :][:, :, ::ds]
            valid   = out_rows < H_out
            data_out[:, out_rows[valid], :sampled.shape[2]] = sampled[:, valid, :]

    return data_out


def _run_inference_on_chunk(
    X_flat: np.ndarray,
    models: dict,
    weights: dict,
    use_gpr: bool,
    use_qrf: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run ensemble inference on a 2-D pixel matrix (N, bands). Returns (pred, lo, hi)."""
    valid = ~np.any(np.isnan(X_flat), axis=1) & ~np.all(X_flat == 0, axis=1)

    pred_vals = np.full(X_flat.shape[0], np.nan, dtype=np.float32)
    lo_vals   = np.full(X_flat.shape[0], np.nan, dtype=np.float32)
    hi_vals   = np.full(X_flat.shape[0], np.nan, dtype=np.float32)

    if not valid.any():
        return pred_vals, lo_vals, hi_vals

    X_valid        = X_flat[valid]
    preds_weighted = np.zeros(X_valid.shape[0], dtype=np.float64)
    lo_weighted    = np.zeros(X_valid.shape[0], dtype=np.float64)
    hi_weighted    = np.zeros(X_valid.shape[0], dtype=np.float64)
    total_w        = 0.0

    if "mapie" in models and "mapie" in weights:
        try:
            # Point prediction via CrossConformalRegressor.predict().
            # Intervals use the precomputed 90th-percentile conformity score.
            mapie = models["mapie"]
            y_p = mapie.predict(X_valid).astype(np.float64)
            w = weights["mapie"]
            preds_weighted += w * y_p
            q = models.get("mapie_q90")
            if q is not None:
                lo_weighted += w * (y_p - q)
                hi_weighted += w * (y_p + q)
            else:
                lo_weighted += w * y_p
                hi_weighted += w * y_p
            total_w += w
        except Exception:
            pass

    if use_gpr and "gpr" in models and "gpr" in weights:
        try:
            gpr_bundle = models["gpr"]
            X_sc = gpr_bundle["scaler"].transform(X_valid)
            y_p, y_std = gpr_bundle["gpr"].predict(X_sc, return_std=True)
            w = weights.get("gpr", 0.0)
            preds_weighted += w * y_p
            lo_weighted    += w * (y_p - 1.645 * y_std)
            hi_weighted    += w * (y_p + 1.645 * y_std)
            total_w        += w
        except Exception:
            pass

    if use_qrf and "qrf" in models and "qrf" in weights:
        try:
            qrf = models["qrf"]
            y_mid = qrf["mid"].predict(X_valid)
            y_lo  = qrf["low"].predict(X_valid)
            y_hi  = qrf["high"].predict(X_valid)
            w = weights.get("qrf", 0.0)
            preds_weighted += w * y_mid
            lo_weighted    += w * y_lo
            hi_weighted    += w * y_hi
            total_w        += w
        except Exception:
            pass

    if total_w > 0:
        pred_vals[valid] = (preds_weighted / total_w).astype(np.float32)
        lo_vals[valid]   = (lo_weighted   / total_w).astype(np.float32)
        hi_vals[valid]   = (hi_weighted   / total_w).astype(np.float32)

    return pred_vals, lo_vals, hi_vals


def predict_raster(
    param: str,
    models: dict,
    stack_path: Path,
    feature_cols: list[str],
    downsample: int = 1,
    use_gpr: bool = True,
    use_qrf: bool = True,
    data_full: np.ndarray | None = None,
    crop_win=None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Predict across the full feature stack in row chunks.

    downsample: spatial reduction factor (e.g. 5 → 1/25 the pixels, ~20x faster).
    use_gpr:    include the GPR ensemble member. Set False to skip it.
    data_full:  pre-loaded (bands, H_out, W_out) array; skips disk I/O entirely
                when predicting multiple params from the same stack.

    Returns (pred, lo, hi, confidence) arrays of shape (H_out, W_out).
    """
    with rasterio.open(stack_path) as src:
        if crop_win is not None:
            H, W = int(crop_win.height), int(crop_win.width)
        else:
            H, W = src.height, src.width
        n_bands = src.count
        nodata  = src.nodata

    ds    = max(1, int(downsample))
    H_out = (H + ds - 1) // ds
    W_out = (W + ds - 1) // ds

    meta    = models.get("meta", {})
    weights = meta.get("ensemble_weights", {"mapie": 1.0})

    pred_arr = np.full((H_out, W_out), np.nan, dtype=np.float32)
    lo_arr   = np.full((H_out, W_out), np.nan, dtype=np.float32)
    hi_arr   = np.full((H_out, W_out), np.nan, dtype=np.float32)

    if ds > 1:
        if data_full is None:
            logger.info(f"  Reading stack via full-res strips (1/{ds} stride)…")
            data_full  = _load_stack_strided(stack_path, ds, crop_win=crop_win)
            _free_after = True
        else:
            _free_after = False

        n_chunks = (H_out + CHUNK_SIZE - 1) // CHUNK_SIZE
        for chunk_i in tqdm(range(n_chunks), desc=f"Predicting {param}"):
            out_rs = chunk_i * CHUNK_SIZE
            out_re = min(out_rs + CHUNK_SIZE, H_out)
            out_h  = out_re - out_rs

            chunk = data_full[:, out_rs:out_re, :]
            X = chunk.reshape(n_bands, -1).T

            p, lo, hi = _run_inference_on_chunk(X, models, weights, use_gpr, use_qrf)
            pred_arr[out_rs:out_re, :] = p.reshape(out_h, W_out)
            lo_arr[out_rs:out_re, :]   = lo.reshape(out_h, W_out)
            hi_arr[out_rs:out_re, :]   = hi.reshape(out_h, W_out)

        if _free_after:
            del data_full

    else:
        with rasterio.open(stack_path) as src:
            n_chunks = (H_out + CHUNK_SIZE - 1) // CHUNK_SIZE
            for chunk_i in tqdm(range(n_chunks), desc=f"Predicting {param}"):
                out_rs = chunk_i * CHUNK_SIZE
                out_re = min(out_rs + CHUNK_SIZE, H_out)
                out_h  = out_re - out_rs

                window = rasterio.windows.Window(0, out_rs, W, out_h)
                data = src.read(window=window).astype(np.float32)
                if nodata is not None:
                    data[data == nodata] = np.nan

                X = data.reshape(n_bands, -1).T
                p, lo, hi = _run_inference_on_chunk(X, models, weights, use_gpr, use_qrf)
                pred_arr[out_rs:out_re, :] = p.reshape(out_h, W)
                lo_arr[out_rs:out_re, :]   = lo.reshape(out_h, W)
                hi_arr[out_rs:out_re, :]   = hi.reshape(out_h, W)

    conf_arr = interval_to_confidence(lo_arr, hi_arr, param)
    return pred_arr, lo_arr, hi_arr, conf_arr


# ---------------------------------------------------------------------------
# Write output GeoTIFFs
# ---------------------------------------------------------------------------

def write_map(array: np.ndarray, path: Path, profile: dict, dtype="float32"):
    p = profile.copy()
    p.update({"dtype": dtype, "count": 1, "compress": "LZW",
              "tiled": True, "blockxsize": 512, "blockysize": 512,
              "BIGTIFF": "IF_SAFER"})
    with rasterio.open(path, "w", **p) as dst:
        dst.write(array.astype(dtype), 1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def predict_param(
    param: str,
    window_label: str,
    downsample: int = 1,
    use_gpr: bool = True,
    use_qrf: bool = True,
    data_full: np.ndarray | None = None,
    stack_window: str | None = None,
    crop_win=None,
):
    effective_stack_window = stack_window or window_label
    stack_path = PROCESSED_DIR / f"feature_stack_{effective_stack_window}.tif"
    if not stack_path.exists():
        logger.error(f"Feature stack not found: {stack_path}. Run 02_feature_engineering.py first.")
        return

    model_files = find_model_files(param, window_label)
    if not model_files:
        logger.error(f"No trained models found for {param} / {window_label}. Run 03_train_models.py first.")
        return

    models       = load_models(model_files)
    feature_cols = models.get("meta", {}).get("feature_cols", [])

    ds_note    = f" (downsample={downsample})" if downsample > 1 else ""
    gpr_note   = " [GPR skipped]" if not use_gpr else ""
    cached     = " [stack cached]" if data_full is not None else ""
    crop_note  = " [Krishna District crop]" if crop_win is not None else ""
    logger.info(f"Predicting {param}{ds_note}{gpr_note}{cached}{crop_note}…")

    pred, lo, hi, conf = predict_raster(
        param, models, stack_path, feature_cols,
        downsample=downsample, use_gpr=use_gpr, use_qrf=use_qrf,
        data_full=data_full, crop_win=crop_win,
    )
    class_arr = classify(pred, param)

    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    # Build output profile — update bounds/dimensions for crop and/or downsample
    with rasterio.open(stack_path) as src:
        profile = src.profile.copy()
        if crop_win is not None:
            crop_bounds = rasterio.windows.bounds(crop_win, src.transform)
        else:
            crop_bounds = src.bounds

    H_out, W_out = pred.shape
    profile.update({
        "height":    H_out,
        "width":     W_out,
        "transform": from_bounds(
            crop_bounds[0], crop_bounds[1], crop_bounds[2], crop_bounds[3],
            W_out, H_out,
        ),
    })

    for arr, suffix, dtype in [
        (pred,      "prediction",  "float32"),
        (lo,        "interval_lo", "float32"),
        (hi,        "interval_hi", "float32"),
        (conf,      "confidence",  "float32"),
        (class_arr, "class",       "uint8"),
    ]:
        out = MAPS_DIR / f"{param}_{window_label}_{suffix}.tif"
        write_map(arr, out, profile, dtype)
        logger.success(f"  → {out.name}")

    valid = ~np.isnan(pred)
    logger.info(
        f"  {param}: mean={np.nanmean(pred):.3f}  "
        f"std={np.nanstd(pred):.3f}  "
        f"avg_confidence={np.nanmean(conf):.2%}"
    )


def main():
    parser = argparse.ArgumentParser(description="Generate soil parameter maps from trained models")
    parser.add_argument("--param",      choices=SOIL_PARAMS)
    parser.add_argument("--all-params", action="store_true")
    parser.add_argument(
        "--window",
        default=BARE_SOIL_WINDOWS[0]["label"],
        choices=[w["label"] for w in BARE_SOIL_WINDOWS],
    )
    parser.add_argument(
        "--combined", action="store_true",
        help="Use models trained on combined_training_data.csv (window label 'combined')",
    )
    parser.add_argument(
        "--downsample", type=int, default=1, metavar="N",
        help="Spatial reduction factor (e.g. 5 → 50m output, ~20x faster). "
             "Dashboard display is unaffected; 500×500 resampling happens at read time.",
    )
    parser.add_argument(
        "--no-gpr", action="store_true",
        help="Skip the GPR ensemble member.",
    )
    parser.add_argument(
        "--no-qrf", action="store_true",
        help="Skip QRF (3 slow GradientBoosting models). MAPIE alone gives calibrated intervals. ~10x faster.",
    )
    parser.add_argument(
        "--krishna", action="store_true",
        help="Crop output to Krishna District bounds only (much faster than full AP).",
    )
    args = parser.parse_args()

    window_label = "combined" if args.combined else args.window
    params = SOIL_PARAMS if args.all_params else ([args.param] if args.param else ["pH", "EC", "OC"])

    stack_window = args.window
    stack_path   = PROCESSED_DIR / f"feature_stack_{stack_window}.tif"

    # Compute crop window for Krishna District if requested
    crop_win = None
    if args.krishna and stack_path.exists():
        minlon, minlat, maxlon, maxlat = KRISHNA_BOUNDS_LATLON
        crop_win = _crop_window(stack_path, minlon, minlat, maxlon, maxlat)
        logger.info(f"Krishna crop window: {int(crop_win.width)}×{int(crop_win.height)} px")

    # Pre-load the feature stack once (cropped if --krishna) and share across params
    data_full = None
    if args.downsample > 1 and len(params) > 1 and stack_path.exists():
        ds = args.downsample
        with rasterio.open(stack_path) as src:
            H = int(crop_win.height) if crop_win else src.height
            W = int(crop_win.width)  if crop_win else src.width
            n_bands = src.count
        H_out, W_out = (H + ds - 1) // ds, (W + ds - 1) // ds
        logger.info(
            f"Pre-loading feature stack → 1/{ds} stride "
            f"({H_out}×{W_out}×{n_bands}, shared across {len(params)} params)…"
        )
        data_full = _load_stack_strided(stack_path, ds, crop_win=crop_win)
        logger.success(f"  Stack loaded ({data_full.nbytes / 1e6:.0f} MB in RAM)")
        data_full = _clip_to_training_bounds(data_full, stack_window)

    for param in params:
        predict_param(
            param, window_label,
            downsample=args.downsample,
            use_gpr=not args.no_gpr,
            use_qrf=not args.no_qrf,
            data_full=data_full,
            stack_window=stack_window if args.combined else None,
            crop_win=crop_win,
        )

    logger.success(f"Maps saved to {MAPS_DIR}")


if __name__ == "__main__":
    main()
