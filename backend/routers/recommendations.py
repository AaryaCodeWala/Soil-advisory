"""Fertilizer recommendation endpoints."""

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pipeline"))
from fertilizer_tables import full_recommendation, DEFAULT_TARGET_YIELD, SOIL_THRESHOLDS
from backend.models import RecommendationRequest, RecommendationResponse

router = APIRouter(prefix="/recommend", tags=["recommendations"])


@router.post("", response_model=RecommendationResponse)
def get_recommendation(req: RecommendationRequest):
    """
    Generate ICAR-calibrated fertilizer recommendation for a field.

    Nutrient Balance Method:
        Dose = (Crop Requirement − Soil Supply) / Fertilizer Use Efficiency
    """
    try:
        result = full_recommendation(
            crop=req.crop,
            soil=req.soil,
            target_yield=req.target_yield,
            area_acres=req.area_acres,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return result


@router.get("/crops")
def list_crops():
    """Return available crops with default target yields."""
    return {
        crop: {"default_yield_t_ha": yld}
        for crop, yld in DEFAULT_TARGET_YIELD.items()
    }


@router.get("/thresholds/{param}")
def get_thresholds(param: str):
    """Return ICAR soil test interpretation thresholds for a parameter."""
    if param not in SOIL_THRESHOLDS:
        raise HTTPException(
            status_code=404,
            detail=f"No thresholds for '{param}'. Available: {list(SOIL_THRESHOLDS)}",
        )
    return {"param": param, "thresholds": SOIL_THRESHOLDS[param]}
