"""
Module 2 — ML Ensemble Training
=================================
Trains three models per soil parameter with spatial k-fold cross-validation:
  1. CatBoost + MAPIE (conformal prediction → calibrated confidence intervals)
  2. Gaussian Process Regressor (Bayesian uncertainty)
  3. Quantile Random Forest (asymmetric uncertainty fallback)

Ensemble is weighted by calibration error on the spatial validation folds.
Models saved with CV metrics embedded in filename.

Usage:
    python pipeline/03_train_models.py [--param pH] [--window post_kharif_2024]
    python pipeline/03_train_models.py --all-params
"""

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from tqdm import tqdm

# Silence minor sklearn/catboost warnings during CV
warnings.filterwarnings("ignore", category=UserWarning)

from config import (
    BARE_SOIL_WINDOWS,
    MODELS_DIR,
    PROCESSED_DIR,
    SOIL_PARAMS,
)

# ---------------------------------------------------------------------------
# Spatial k-fold cross-validation
# ---------------------------------------------------------------------------

def spatial_kfold_splits(
    df: pd.DataFrame,
    lat_col: str = "lat",
    lon_col: str = "lon",
    n_folds: int = 5,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """
    Block spatial k-fold: divide AP into a n×n grid, assign each sample
    to a block, then leave one block out at a time.

    This prevents spatial autocorrelation leakage that random CV ignores —
    nearby SHC points share similar soil/spectral conditions, so random splits
    give inflated accuracy estimates.
    """
    from sklearn.cluster import KMeans

    coords = df[[lat_col, lon_col]].values
    # KMeans on spatial coordinates gives compact, spatially coherent folds
    kmeans = KMeans(n_clusters=n_folds, n_init=10, random_state=42)
    blocks = kmeans.fit_predict(coords)

    splits = []
    for fold in range(n_folds):
        val_idx   = np.where(blocks == fold)[0]
        train_idx = np.where(blocks != fold)[0]
        splits.append((train_idx, val_idx))
    return splits


# ---------------------------------------------------------------------------
# Model builders
# ---------------------------------------------------------------------------

def build_catboost(X_train, y_train, param: str):
    from catboost import CatBoostRegressor
    model = CatBoostRegressor(
        iterations=1000,
        learning_rate=0.05,
        depth=6,
        loss_function="RMSE",
        eval_metric="RMSE",
        early_stopping_rounds=50,
        random_seed=42,
        verbose=0,
        task_type="GPU",   # ← added
        devices="0",       # ← added
    )
    model.fit(X_train, y_train)
    return model


def build_mapie_catboost(X_train, y_train, param: str):
    from catboost import CatBoostRegressor
    from mapie.regression import CrossConformalRegressor

    base = CatBoostRegressor(
        iterations=300,
        learning_rate=0.08,
        depth=6,
        random_seed=42,
        verbose=0,
        task_type="GPU",   # ← added
        devices="0",       # ← added
    )
    mapie = CrossConformalRegressor(
        estimator=base,
        confidence_level=0.90,
        method="plus",
        cv=3,
        n_jobs=1,
    )
    mapie.fit_conformalize(X_train, y_train)
    return mapie


def build_gpr(X_train, y_train, param: str):
    """
    Gaussian Process with RBF + WhiteKernel.
    Uses sklearn GPR (not GPyTorch) for datasets up to ~2000 points.
    Above that we switch to sparse GP approximation.
    """
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel
    from sklearn.preprocessing import StandardScaler

    scaler  = StandardScaler()
    X_sc    = scaler.fit_transform(X_train)

    # Use RBF kernel — appropriate for smooth spatial variation
    kernel = ConstantKernel(1.0) * RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1)

    if len(X_train) > 2000:
        # Too many points for exact GP — subsample for kernel fitting
        idx   = np.random.choice(len(X_train), 2000, replace=False)
        X_fit = X_sc[idx]
        y_fit = y_train.iloc[idx] if hasattr(y_train, "iloc") else y_train[idx]
    else:
        X_fit, y_fit = X_sc, y_train

    gpr = GaussianProcessRegressor(kernel=kernel, alpha=1e-6, n_restarts_optimizer=3)
    gpr.fit(X_fit, y_fit)
    return gpr, scaler


def build_qrf(X_train, y_train, param: str):
    """Quantile Random Forest for asymmetric uncertainty bounds."""
    from sklearn.ensemble import GradientBoostingRegressor

    # Train three models: median (0.5), lower (0.05), upper (0.95) quantiles
    models = {}
    for q, name in [(0.05, "low"), (0.50, "mid"), (0.95, "high")]:
        m = GradientBoostingRegressor(
            loss="quantile",
            alpha=q,
            n_estimators=100,
            max_depth=4,
            learning_rate=0.08,
            random_state=42,
        )
        m.fit(X_train, y_train)
        models[name] = m
    return models


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(y_true, y_pred, y_lo=None, y_hi=None) -> dict:
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae  = mean_absolute_error(y_true, y_pred)
    r2   = r2_score(y_true, y_pred)

    metrics = {"RMSE": round(rmse, 4), "MAE": round(mae, 4), "R2": round(r2, 4)}

    if y_lo is not None and y_hi is not None:
        # Coverage: fraction of true values inside the prediction interval
        coverage = np.mean((y_true >= y_lo) & (y_true <= y_hi))
        avg_width = np.mean(y_hi - y_lo)
        # Calibration error: |empirical_coverage - target_coverage| (target=90%)
        cal_error = abs(coverage - 0.90)
        metrics.update({
            "coverage_90": round(float(coverage), 4),
            "interval_width": round(float(avg_width), 4),
            "calibration_error": round(float(cal_error), 4),
        })
    return metrics


# ---------------------------------------------------------------------------
# Single-parameter training
# ---------------------------------------------------------------------------

def train_for_param(
    param: str,
    df: pd.DataFrame,
    feature_cols: list[str],
    window_label: str,
):
    label_col = f"label_{param}"
    if label_col not in df.columns:
        logger.warning(f"No labels for {param} — skipping.")
        return

    # Drop rows with missing label or features
    sub = df[feature_cols + [label_col, "lat", "lon"]].dropna()
    if len(sub) < 30:
        logger.warning(f"{param}: only {len(sub)} samples — too few to train reliably.")
        return

    X = sub[feature_cols].values.astype(np.float32)
    y = sub[label_col].values.astype(np.float32)

    logger.info(f"\n── {param}: {len(sub)} samples ──────────────────────────────")

    splits = spatial_kfold_splits(sub, n_folds=min(5, len(sub) // 10))

    cv_metrics = {"mapie": [], "gpr": [], "qrf": []}

    for fold_i, (train_idx, val_idx) in enumerate(splits):
        X_tr, X_val = X[train_idx], X[val_idx]
        y_tr, y_val = y[train_idx], y[val_idx]

        if len(X_val) == 0:
            continue

        # MAPIE / CatBoost
        try:
            mapie = build_mapie_catboost(X_tr, y_tr, param)
            y_pred_mapie, intervals = mapie.predict_interval(X_val)
            y_lo = intervals[:, 0, 0]
            y_hi = intervals[:, 1, 0]
            m = compute_metrics(y_val, y_pred_mapie, y_lo, y_hi)
            cv_metrics["mapie"].append(m)
        except Exception as e:
            logger.debug(f"  MAPIE fold {fold_i} failed: {e}")

        # GPR
        try:
            gpr, scaler = build_gpr(X_tr, y_tr, param)
            X_val_sc = scaler.transform(X_val)
            y_pred_gpr, y_std = gpr.predict(X_val_sc, return_std=True)
            y_lo_gpr = y_pred_gpr - 1.645 * y_std
            y_hi_gpr = y_pred_gpr + 1.645 * y_std
            m = compute_metrics(y_val, y_pred_gpr, y_lo_gpr, y_hi_gpr)
            cv_metrics["gpr"].append(m)
        except Exception as e:
            logger.debug(f"  GPR fold {fold_i} failed: {e}")

        # QRF
        try:
            qrf = build_qrf(X_tr, y_tr, param)
            y_pred_qrf = qrf["mid"].predict(X_val)
            y_lo_qrf   = qrf["low"].predict(X_val)
            y_hi_qrf   = qrf["high"].predict(X_val)
            m = compute_metrics(y_val, y_pred_qrf, y_lo_qrf, y_hi_qrf)
            cv_metrics["qrf"].append(m)
        except Exception as e:
            logger.debug(f"  QRF fold {fold_i} failed: {e}")

    # Average CV metrics across folds
    def avg_metrics(fold_list):
        if not fold_list:
            return {}
        keys = fold_list[0].keys()
        return {k: round(np.mean([f[k] for f in fold_list]), 4) for k in keys}

    avg = {name: avg_metrics(folds) for name, folds in cv_metrics.items()}

    # Log CV results
    for model_name, m in avg.items():
        if m:
            logger.info(
                f"  {model_name:6s} CV — RMSE={m.get('RMSE', '?'):.4f}  "
                f"R²={m.get('R2', '?'):.3f}  "
                f"Coverage={m.get('coverage_90', '?'):.2%}  "
                f"CalErr={m.get('calibration_error', '?'):.4f}"
            )

    # Ensemble weights: inverse calibration error (lower cal_error = better uncertainty)
    weights = {}
    for name, m in avg.items():
        cal_err = m.get("calibration_error", 1.0)
        weights[name] = 1.0 / (cal_err + 1e-6)
    total = sum(weights.values())
    weights = {k: v / total for k, v in weights.items()}
    logger.info(f"  Ensemble weights: { {k: round(v, 3) for k, v in weights.items()} }")

    # ── Train final models on ALL data ───────────────────────────────────────
    logger.info(f"  Training final models on full dataset ({len(X)} samples)…")

    final_mapie, final_gpr, final_gpr_scaler, final_qrf = None, None, None, None
    try:
        final_mapie = build_mapie_catboost(X, y, param)
    except Exception as e:
        logger.warning(f"  Final MAPIE failed: {e}")
    try:
        final_gpr, final_gpr_scaler = build_gpr(X, y, param)
    except Exception as e:
        logger.warning(f"  Final GPR failed: {e}")
    try:
        final_qrf = build_qrf(X, y, param)
    except Exception as e:
        logger.warning(f"  Final QRF failed: {e}")

    # ── Save artefacts ────────────────────────────────────────────────────────
    import joblib

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    best_rmse = avg.get("mapie", {}).get("RMSE", avg.get("gpr", {}).get("RMSE", 9999))
    best_r2   = avg.get("mapie", {}).get("R2",   avg.get("gpr", {}).get("R2",   0))

    stem = f"{param}_{window_label}_rmse{best_rmse:.3f}_r2{best_r2:.3f}"

    if final_mapie:
        joblib.dump(final_mapie, MODELS_DIR / f"{stem}_mapie.pkl")
    if final_gpr:
        joblib.dump({"gpr": final_gpr, "scaler": final_gpr_scaler},
                    MODELS_DIR / f"{stem}_gpr.pkl")
    if final_qrf:
        joblib.dump(final_qrf, MODELS_DIR / f"{stem}_qrf.pkl")

    # Save CV metrics + weights as JSON for the prediction step
    meta = {
        "param":          param,
        "window":         window_label,
        "n_samples":      len(sub),
        "feature_cols":   feature_cols,
        "cv_metrics":     avg,
        "ensemble_weights": weights,
    }
    with open(MODELS_DIR / f"{stem}_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    logger.success(
        f"  Saved models → {MODELS_DIR}/{stem}_[mapie|gpr|qrf].pkl"
    )
    return meta


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Train soil parameter models")
    parser.add_argument("--param", choices=SOIL_PARAMS, help="Single parameter to train")
    parser.add_argument("--all-params", action="store_true", help="Train all parameters")
    parser.add_argument(
        "--window",
        default=BARE_SOIL_WINDOWS[0]["label"],
        choices=[w["label"] for w in BARE_SOIL_WINDOWS],
    )
    parser.add_argument(
        "--combined", action="store_true",
        help="Use combined_training_data.csv (real + synthetic, 5299 rows) instead of window-specific CSV",
    )
    parser.add_argument(
        "--skip-done", action="store_true",
        help="Skip parameters that already have a saved model in data/models/",
    )
    args = parser.parse_args()

    params_to_train = SOIL_PARAMS if args.all_params else ([args.param] if args.param else ["pH", "EC", "OC"])

    if args.skip_done:
        done = {f.name.split("_")[0] for f in MODELS_DIR.glob("*_combined_*_meta.json")}
        before = params_to_train[:]
        params_to_train = [p for p in params_to_train if p not in done]
        logger.info(f"Skipping already-trained: {sorted(done & set(before))}")
        logger.info(f"Remaining: {params_to_train}")

    if args.combined:
        csv_path = PROCESSED_DIR / "combined_training_data.csv"
        window_label = "combined"
    else:
        csv_path = PROCESSED_DIR / f"training_data_{args.window}.csv"
        window_label = args.window

    if not csv_path.exists():
        logger.error(f"Training data not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    # Drop synthetic-only marker column if present
    if "source" in df.columns:
        df = df.drop(columns=["source"])
    logger.info(f"Loaded training data: {len(df):,} rows, {len(df.columns)} columns")

    feature_cols = [
        c for c in df.columns
        if not c.startswith("label_")
        and c not in ["farmer_id", "village", "mandal", "district",
                      "sample_date", "geometry_wkt", "lat", "lon"]
    ]
    logger.info(f"Feature columns: {len(feature_cols)}")

    all_meta = []
    for param in params_to_train:
        meta = train_for_param(param, df, feature_cols, window_label)
        if meta:
            all_meta.append(meta)

    # Summary table
    logger.info("\n── Training Summary ────────────────────────────────────────")
    logger.info(f"  {'Param':6s}  {'RMSE':>8s}  {'R²':>6s}  {'Coverage':>10s}")
    for meta in all_meta:
        m = meta["cv_metrics"].get("mapie", meta["cv_metrics"].get("gpr", {}))
        logger.info(
            f"  {meta['param']:6s}  {m.get('RMSE', '—'):>8.4f}  "
            f"{m.get('R2', '—'):>6.3f}  {m.get('coverage_90', '—'):>10.2%}"
        )


if __name__ == "__main__":
    main()
