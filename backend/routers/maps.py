"""Map data endpoints — raster statistics and GeoJSON point samples."""

import io
import sys
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pipeline"))
from config import PROCESSED_DIR, SOIL_PARAMS, BARE_SOIL_WINDOWS, HIGH_CONFIDENCE_THRESHOLD
from fertilizer_tables import SOIL_THRESHOLDS
from backend.models import MapStats, PointCollection, PointFeature, ParameterStatus

try:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import transform as warp_transform
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

router = APIRouter(prefix="/maps", tags=["maps"])

MAPS_DIR = PROCESSED_DIR / "maps"
_FALLBACK_WINDOW = BARE_SOIL_WINDOWS[0]["label"]

def _default_window() -> str:
    """Prefer combined models if they exist, else fall back to first satellite window."""
    if (MAPS_DIR / f"pH_combined_prediction.tif").exists():
        return "combined"
    return _FALLBACK_WINDOW

DEFAULT_WINDOW = _default_window()


def _pred_path(param: str, window: str) -> Path:
    return MAPS_DIR / f"{param}_{window}_prediction.tif"


def _conf_path(param: str, window: str) -> Path:
    return MAPS_DIR / f"{param}_{window}_confidence.tif"


def _require_rasterio():
    if not HAS_RASTERIO:
        raise HTTPException(status_code=500, detail="rasterio not installed")


def _require_map(path: Path):
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Map not found: {path.name}. Run pipeline/05_predict_maps.py first.",
        )


def _deficiency_pct(values: np.ndarray, param: str) -> float:
    """Fraction of valid pixels classified as deficient/low."""
    thresholds = SOIL_THRESHOLDS.get(param, {})
    if param == "pH":
        low_mask = (values < 6.5) | (values > 7.5)
    elif "deficient" in thresholds:
        thr = thresholds["deficient"][1]
        low_mask = values < thr
    else:
        items = list(thresholds.items())
        if not items:
            return 0.0
        low_mask = values < items[0][1][1]
    valid = ~np.isnan(values)
    if not valid.any():
        return 0.0
    return float(np.sum(low_mask & valid) / valid.sum() * 100)


@router.get("/status")
def map_status(window: str = None) -> list[ParameterStatus]:
    """List all parameters and whether their prediction maps exist."""
    window = window or _default_window()
    result = []
    for param in SOIL_PARAMS:
        pp = _pred_path(param, window)
        cp = _conf_path(param, window)
        result.append(ParameterStatus(
            param=param,
            window=window,
            available=pp.exists(),
            prediction_file=pp.name if pp.exists() else None,
            confidence_file=cp.name if cp.exists() else None,
        ))
    return result


@router.get("/{param}/stats", response_model=MapStats)
def map_stats(param: str, window: str = None):
    window = window or _default_window()
    """
    Compute summary statistics for a prediction map.
    Downsamples to 500×500 for speed.
    """
    _require_rasterio()
    if param not in SOIL_PARAMS:
        raise HTTPException(status_code=404, detail=f"Unknown param '{param}'")

    pred_path = _pred_path(param, window)
    conf_path = _conf_path(param, window)
    _require_map(pred_path)

    with rasterio.open(pred_path) as src:
        data = src.read(
            1, out_shape=(500, 500), resampling=Resampling.average
        ).astype(np.float32)
        nodata = src.nodata

    if nodata is not None:
        data[data == nodata] = np.nan

    valid = data[~np.isnan(data)]
    if valid.size == 0:
        raise HTTPException(status_code=422, detail="Map contains no valid pixels")

    avg_conf = 0.0
    high_conf_pct = 0.0
    if conf_path.exists():
        with rasterio.open(conf_path) as src:
            conf = src.read(
                1, out_shape=(500, 500), resampling=Resampling.average
            ).astype(np.float32)
        conf_valid = conf[~np.isnan(conf)]
        if conf_valid.size > 0:
            avg_conf = float(np.nanmean(conf_valid))
            high_conf_pct = float(np.mean(conf_valid >= HIGH_CONFIDENCE_THRESHOLD) * 100)

    return MapStats(
        param=param,
        window=window,
        count_valid_pixels=int(valid.size),
        mean=round(float(np.mean(valid)), 4),
        std=round(float(np.std(valid)), 4),
        p5=round(float(np.percentile(valid, 5)), 4),
        p25=round(float(np.percentile(valid, 25)), 4),
        median=round(float(np.percentile(valid, 50)), 4),
        p75=round(float(np.percentile(valid, 75)), 4),
        p95=round(float(np.percentile(valid, 95)), 4),
        deficiency_pct=round(_deficiency_pct(data, param), 1),
        avg_confidence=round(avg_conf, 4),
        high_confidence_pct=round(high_conf_pct, 1),
    )


@router.get("/{param}/points", response_model=PointCollection)
def map_points(
    param: str,
    window: str = None,
    n: int = Query(2000, ge=100, le=10000, description="Number of random sample points"),
):
    window = window or _default_window()
    """
    Return a GeoJSON FeatureCollection of n random sample points from a prediction map.
    Coordinates are in WGS84 (EPSG:4326) for direct use in web maps.
    Each feature has: value, confidence, deficiency_class properties.
    """
    _require_rasterio()
    if param not in SOIL_PARAMS:
        raise HTTPException(status_code=404, detail=f"Unknown param '{param}'")

    pred_path = _pred_path(param, window)
    conf_path = _conf_path(param, window)
    _require_map(pred_path)

    with rasterio.open(pred_path) as src:
        data = src.read(
            1, out_shape=(500, 500), resampling=Resampling.average
        ).astype(np.float32)
        nodata  = src.nodata
        bounds  = src.bounds
        src_crs = src.crs

    if nodata is not None:
        data[data == nodata] = np.nan

    conf_data = np.full_like(data, np.nan)
    if conf_path.exists():
        with rasterio.open(conf_path) as src:
            conf_data = src.read(
                1, out_shape=(500, 500), resampling=Resampling.average
            ).astype(np.float32)

    H, W = data.shape
    rows_idx, cols_idx = np.where(~np.isnan(data))
    if len(rows_idx) == 0:
        raise HTTPException(status_code=422, detail="Map contains no valid pixels")

    rng = np.random.default_rng(42)
    sample_idx = rng.choice(len(rows_idx), size=min(n, len(rows_idx)), replace=False)
    r = rows_idx[sample_idx]
    c = cols_idx[sample_idx]

    # Convert pixel indices → UTM coordinates → WGS84
    x_utm = bounds.left + (c + 0.5) / W * (bounds.right - bounds.left)
    y_utm = bounds.top  - (r + 0.5) / H * (bounds.top - bounds.bottom)
    xs, ys = warp_transform(src_crs, "EPSG:4326", x_utm.tolist(), y_utm.tolist())

    thresholds = SOIL_THRESHOLDS.get(param, {})

    features = []
    for i in range(len(r)):
        val  = float(data[r[i], c[i]])
        conf = float(conf_data[r[i], c[i]]) if not np.isnan(conf_data[r[i], c[i]]) else None

        # Deficiency class
        if param == "pH":
            cls = "acid" if val < 6.5 else ("alkaline" if val > 7.5 else "optimal")
        elif "deficient" in thresholds:
            cls = "deficient" if val < thresholds["deficient"][1] else "adequate"
        else:
            items = list(thresholds.items())
            if len(items) >= 2 and val < items[0][1][1]:
                cls = items[0][0]
            elif len(items) >= 3 and val < items[1][1][1]:
                cls = items[1][0]
            else:
                cls = items[-1][0] if items else "unknown"

        features.append(PointFeature(
            geometry={"type": "Point", "coordinates": [round(xs[i], 6), round(ys[i], 6)]},
            properties={"value": round(val, 4), "confidence": conf, "class": cls},
        ))

    return PointCollection(
        features=features,
        param=param,
        window=window,
        n_points=len(features),
    )


@router.get("/{param}/raster.png")
def raster_png(
    param: str,
    window: str = None,
    layer: str = Query("prediction", description="'prediction' or 'confidence'"),
    invert: bool = False,
):
    """
    Render a prediction or confidence raster as an RGBA PNG with a RdYlGn colormap.
    Nodata pixels are transparent. Used by the frontend SVG map overlay.
    """
    _require_rasterio()
    if param not in SOIL_PARAMS:
        raise HTTPException(status_code=404, detail=f"Unknown param '{param}'")

    window = window or _default_window()
    path = _conf_path(param, window) if layer == "confidence" else _pred_path(param, window)
    _require_map(path)

    with rasterio.open(path) as src:
        data = src.read(1, out_shape=(400, 400), resampling=Resampling.average).astype(np.float32)
        nodata = src.nodata

    if nodata is not None:
        data[data == nodata] = np.nan

    valid_mask = ~np.isnan(data)
    if not valid_mask.any():
        raise HTTPException(status_code=422, detail="No valid pixels")

    v_min = float(np.nanpercentile(data, 2))
    v_max = float(np.nanpercentile(data, 98))
    if v_max == v_min:
        v_max = v_min + 1.0

    norm = np.clip((data - v_min) / (v_max - v_min), 0.0, 1.0)
    if invert:
        norm = 1.0 - norm

    # RdYlGn colormap: red=0 (deficient), yellow=0.5, green=1 (optimal)
    import matplotlib.cm as cm
    cmap = cm.RdYlGn
    rgba = (cmap(norm) * 255).astype(np.uint8)
    rgba[~valid_mask, 3] = 0  # transparent nodata

    from PIL import Image
    img = Image.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )
