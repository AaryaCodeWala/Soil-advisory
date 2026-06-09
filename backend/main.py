"""
Soil Advisory API — FastAPI backend
=====================================
Run with:
    uvicorn backend.main:app --reload --port 8000

Interactive docs at:
    http://localhost:8000/docs   (Swagger UI)
    http://localhost:8000/redoc  (ReDoc)
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))

from backend.routers import recommendations, maps, sms, suitability, weather

app = FastAPI(
    title="Soil Advisory API — Andhra Pradesh",
    description=(
        "AI-enabled soil nutrient mapping and fertilizer recommendation API. "
        "Serves prediction map statistics, GeoJSON point samples, and ICAR-calibrated "
        "fertilizer recommendations for paddy, cotton, groundnut, and red gram."
    ),
    version="1.0.0",
    contact={"name": "Agriculture Department, Government of Andhra Pradesh"},
)

# Allow the Dash dashboard (port 8050) and any other local client to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8050", "http://localhost:3000", "*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(recommendations.router, prefix="/api")
app.include_router(maps.router,            prefix="/api")
app.include_router(sms.router,             prefix="/api")
app.include_router(suitability.router,     prefix="/api")
app.include_router(weather.router,         prefix="/api")


@app.get("/api/health", tags=["health"])
def health():
    """Liveness check."""
    return {"status": "ok", "service": "soil-advisory-api"}


@app.get("/api/params", tags=["health"])
def list_params():
    """Return the list of modelled soil parameters."""
    from config import SOIL_PARAMS, BARE_SOIL_WINDOWS
    return {
        "params": SOIL_PARAMS,
        "windows": [w["label"] for w in BARE_SOIL_WINDOWS],
    }
