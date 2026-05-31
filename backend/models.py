"""Pydantic request/response schemas for the Soil Advisory API."""

from typing import Literal
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class RecommendationRequest(BaseModel):
    crop: Literal["paddy", "cotton", "groundnut", "red_gram"]
    soil: dict[str, float] = Field(
        ...,
        example={
            "pH": 6.8, "EC": 0.4, "OC": 0.45,
            "N": 220.0, "P": 18.0, "K": 150.0,
            "Fe": 3.2, "Cu": 0.15, "B": 0.3, "Zn": 0.4,
        },
        description="Soil test values keyed by parameter name",
    )
    target_yield: float | None = Field(
        None,
        description="Target yield in t/ha. Uses ICAR default for the crop if omitted.",
    )
    area_acres: float = Field(
        1.0,
        gt=0,
        description="Field area in acres used to compute total quantities and cost savings.",
    )


# ---------------------------------------------------------------------------
# Response bodies
# ---------------------------------------------------------------------------

class NutrientDose(BaseModel):
    nutrient: str
    crop_requirement: float
    soil_supply: float
    net_requirement: float
    dose_kg_ha: float
    splits: list[dict]


class MicronutrientAlert(BaseModel):
    nutrient: str
    carrier: str
    dose_kg_ha: float
    dose_kg_acre: float
    timing: str
    foliar: str | None


class RecommendationResponse(BaseModel):
    crop: str
    area_acres: float
    target_yield_t_ha: float
    macronutrients: dict[str, NutrientDose]
    micronutrients: list[MicronutrientAlert]
    estimated_savings_inr: float


class MapStats(BaseModel):
    param: str
    window: str
    count_valid_pixels: int
    mean: float
    std: float
    p5: float
    p25: float
    median: float
    p75: float
    p95: float
    deficiency_pct: float
    avg_confidence: float
    high_confidence_pct: float


class PointFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: dict
    properties: dict


class PointCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[PointFeature]
    param: str
    window: str
    n_points: int


class ParameterStatus(BaseModel):
    param: str
    window: str
    available: bool
    prediction_file: str | None
    confidence_file: str | None
