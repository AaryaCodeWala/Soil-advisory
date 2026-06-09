"""Crop suitability advisory endpoint."""

import sys
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pipeline"))
from crop_suitability import rank_crops

router = APIRouter(prefix="/suitability", tags=["suitability"])


class SoilInput(BaseModel):
    pH:  float = Field(7.0,  ge=0,   le=14,  description="Soil pH")
    EC:  float = Field(0.4,  ge=0,   le=20,  description="Electrical conductivity (dS/m)")
    OC:  float = Field(0.5,  ge=0,   le=10,  description="Organic carbon (%)")
    N:   float = Field(200,  ge=0,   le=999, description="Available nitrogen (kg/ha)")
    P:   float = Field(20,   ge=0,   le=200, description="Available phosphorus (kg/ha)")
    K:   float = Field(150,  ge=0,   le=999, description="Available potassium (kg/ha)")
    Fe:  float = Field(4.5,  ge=0,   le=100, description="Iron (ppm)")
    Cu:  float = Field(0.5,  ge=0,   le=10,  description="Copper (ppm)")
    B:   float = Field(0.5,  ge=0,   le=10,  description="Boron (ppm)")
    Zn:  float = Field(0.6,  ge=0,   le=10,  description="Zinc (ppm)")


@router.post("")
def crop_suitability(soil: SoilInput):
    """
    Score and rank all four AP focus crops (paddy, cotton, groundnut, red_gram)
    against the provided soil measurements using ICAR threshold-based rules.

    Returns a ranked list with scores, grade labels, constraint warnings,
    and a plain-language summary suitable for display in the farmer advisory.
    """
    return rank_crops(soil.model_dump())
