"""SMS generation endpoint."""

import sys
from pathlib import Path
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "pipeline"))
from fertilizer_tables import full_recommendation
from sms_formatter import format_sms

router = APIRouter(prefix="/sms", tags=["sms"])


class SMSRequest(BaseModel):
    crop: str = Field(..., examples=["paddy"])
    soil: dict = Field(
        ...,
        examples=[{"pH": 6.8, "EC": 0.45, "OC": 0.52, "N": 210, "P": 14, "K": 145,
                   "Fe": 3.2, "Zn": 0.3, "B": 0.8, "Cu": 0.25}],
    )
    target_yield: float | None = Field(None, description="t/ha; uses ICAR default if omitted")
    area_acres: float = Field(1.0, ge=0.1)
    farmer_name: str = Field("", description="Optional farmer name to personalise message")
    lang: Literal["en", "te", "both"] = Field("both")
    mode: Literal["short", "full"] = Field(
        "short",
        description="short=1-2 segments (totals only); full=2-3 segments (split schedule)",
    )


class SMSResponse(BaseModel):
    en: str | None = None
    en_segs: int | None = None
    en_chars: int | None = None
    te: str | None = None
    te_segs: int | None = None
    te_chars: int | None = None


@router.post("", response_model=SMSResponse)
def generate_sms(req: SMSRequest):
    """
    Generate bilingual fertilizer advisory SMS for a field.

    Returns formatted English and/or Telugu text ready to dispatch
    via any SMS gateway (e.g., BSNL BulkSMS, MSG91).
    """
    rec = full_recommendation(
        crop=req.crop,
        soil=req.soil,
        target_yield=req.target_yield,
        area_acres=req.area_acres,
    )
    return format_sms(
        rec,
        lang=req.lang,
        farmer_name=req.farmer_name,
        mode=req.mode,
    )
