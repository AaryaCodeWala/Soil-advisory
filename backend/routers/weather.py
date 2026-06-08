"""
Weather-aware fertilizer timing endpoint.

Uses the Open-Meteo API (free, no key) to fetch a 7-day rain forecast for
Krishna District and translate it into actionable application advice:
  - Apply today / safe window
  - Delay N days — rain expected
  - Risk level per day (low / medium / high)

Open-Meteo docs: https://open-meteo.com/en/docs
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/weather", tags=["weather"])

# Krishna District centroid (WGS84)
KRISHNA_LAT = 16.35
KRISHNA_LON = 80.75

# Risk thresholds
RISK_HIGH_PROB   = 65   # % precipitation probability → high risk
RISK_MED_PROB    = 40   # bump for AP monsoon baseline cloudiness
RISK_HIGH_MM     = 10   # mm expected → high risk
RISK_MED_MM      = 3

IST = timezone(timedelta(hours=5, minutes=30))


def _fetch_open_meteo(lat: float, lon: float) -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=precipitation_sum,precipitation_probability_max,weathercode"
        "&forecast_days=7"
        "&timezone=Asia%2FKolkata"
    )
    try:
        with urllib.request.urlopen(url, timeout=6) as r:
            return json.loads(r.read())
    except urllib.error.URLError as e:
        raise HTTPException(status_code=503, detail=f"Weather API unavailable: {e}")


def _risk(prob: float, mm: float) -> str:
    if prob >= RISK_HIGH_PROB or mm >= RISK_HIGH_MM:
        return "high"
    if prob >= RISK_MED_PROB or mm >= RISK_MED_MM:
        return "medium"
    return "low"


def _wmo_label(code: int) -> str:
    """Translate WMO weather code to a short description."""
    if code == 0:            return "Clear"
    if code in (1, 2, 3):   return "Partly cloudy"
    if code in range(51,58): return "Drizzle"
    if code in range(61,68): return "Rain"
    if code in range(71,78): return "Snow"
    if code in range(80,83): return "Showers"
    if code in range(95,100):return "Thunderstorm"
    return "Cloudy"


@router.get("/timing")
def weather_timing(
    lat: float = Query(KRISHNA_LAT, description="Latitude (default: Krishna District)"),
    lon: float = Query(KRISHNA_LON, description="Longitude (default: Krishna District)"),
):
    """
    Return a 7-day rain forecast with per-day fertilizer application risk levels
    and a plain-language advice string.
    """
    raw = _fetch_open_meteo(lat, lon)

    daily  = raw["daily"]
    dates  = daily["time"]
    probs  = daily["precipitation_probability_max"]
    mms    = daily["precipitation_sum"]
    codes  = daily.get("weathercode", [0] * 7)

    today = datetime.now(IST).date()
    days  = []
    safe_windows: list[str] = []

    for i, date_str in enumerate(dates):
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        prob = probs[i] or 0
        mm   = mms[i]   or 0
        risk = _risk(prob, mm)
        safe = risk == "low"

        day_label = "Today" if date == today else (
            "Tomorrow" if date == today + timedelta(days=1) else
            date.strftime("%a")
        )

        days.append({
            "date":      date_str,
            "day_label": day_label,
            "rain_mm":   round(mm, 1),
            "rain_prob": int(prob),
            "weather":   _wmo_label(codes[i]),
            "risk":      risk,
            "apply":     safe,
        })
        if safe:
            safe_windows.append(date_str)

    # Build advice string
    today_risk     = days[0]["risk"]
    tomorrow_risk  = days[1]["risk"] if len(days) > 1 else "low"
    next_safe      = safe_windows[0] if safe_windows else None

    if today_risk == "low":
        if tomorrow_risk == "low":
            advice = "Conditions are good. Safe to apply fertilizer today or tomorrow."
        else:
            advice = "Apply today — rain is likely tomorrow. Avoid runoff risk."
    elif today_risk == "medium":
        delay_days = next((i for i, d in enumerate(days) if d["risk"] == "low"), None)
        if delay_days is not None:
            advice = f"Moderate rain risk today. Best to wait {delay_days} day{'s' if delay_days>1 else ''} — safer window on {days[delay_days]['day_label']}."
        else:
            advice = "Unsettled weather all week. Apply in early morning before any rain if needed."
    else:
        delay_days = next((i for i, d in enumerate(days) if d["risk"] == "low"), None)
        if delay_days is not None:
            advice = f"Heavy rain expected. Delay application by {delay_days} day{'s' if delay_days>1 else ''} to prevent nutrient runoff — next safe window: {days[delay_days]['day_label']}."
        else:
            advice = "High rain risk all week. Avoid applying — fertilizer runoff will waste money and pollute waterways."

    return {
        "location":     "Krishna District, Andhra Pradesh",
        "fetched_at":   datetime.now(IST).strftime("%Y-%m-%d %H:%M IST"),
        "days":         days,
        "advice":       advice,
        "safe_windows": safe_windows,
        "next_safe":    next_safe,
        "today_risk":   today_risk,
    }
