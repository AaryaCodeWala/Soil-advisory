"""
Rule-based crop suitability scoring for Krishna District, AP.

Each crop is scored against measured soil parameters using ICAR soil-test
interpretation thresholds calibrated for the Andhra Pradesh agro-climatic zone.

Score bands:
  80-100  Highly Suitable  — grow with confidence
  60-79   Suitable         — minor constraints, manageable
  40-59   Marginal         — significant constraints, expect yield penalty
  0-39    Unsuitable       — do not recommend this season
"""

from __future__ import annotations
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Crop profile definitions
# ---------------------------------------------------------------------------
# Each "rule" tuple: (param, opt_lo, opt_hi, marg_lo, marg_hi, weight,
#                     msg_if_too_high, msg_if_too_low)
# weight=4 means a critical parameter; weight=1 means minor influence.
# ---------------------------------------------------------------------------

PROFILES: dict[str, dict] = {
    "paddy": {
        "display":    "Paddy",
        "display_te": "వరి",
        "emoji":      "🌾",
        "desc":       "Prefers neutral pH, low salinity, and good water retention.",
        "rules": [
            ("pH",  6.0, 7.5, 5.0, 8.5, 2,
             "Alkaline soil reduces Fe/Zn availability critical for paddy",
             "Acidic soil suppresses nutrient uptake in paddy"),
            ("EC",  0.0, 1.0, 0.0, 2.0, 5,
             "Paddy is salt-sensitive — yield drops sharply above EC 1.0 dS/m",
             None),
            ("OC",  0.5, 2.5, 0.3, 2.5, 2,
             None,
             "Low organic carbon limits paddy yield and tillering"),
            ("N",   140, 420, 80,  560,  1,
             None,
             "Low available N — paddy is a high N-demand crop"),
            ("Fe",  4.5, 20,  2.5, 20,   2,
             None,
             "Iron deficiency causes bronzing/yellowing — common in AP paddy"),
        ],
    },

    "cotton": {
        "display":    "Cotton",
        "display_te": "పత్తి",
        "emoji":      "🌿",
        "desc":       "Tolerates moderate salinity and alkalinity; needs high K.",
        "rules": [
            ("pH",  6.5, 8.0, 5.5, 8.5, 2,
             "Very high pH limits micronutrient uptake in cotton",
             "Acidic soil reduces cotton lint quality"),
            ("EC",  0.0, 3.0, 0.0, 4.0, 3,
             "Salinity above 3 dS/m reduces cotton germination and boll set",
             None),
            ("OC",  0.4, 2.5, 0.25, 2.5, 1,
             None,
             "Low OC — cotton benefits from improved soil structure"),
            ("K",   150, 600, 80,  600,  3,
             None,
             "Potassium deficiency causes premature boll shedding in cotton"),
            ("N",   140, 420, 80,  560,  1,
             None,
             "Low N — cotton needs moderate nitrogen for vegetative growth"),
        ],
    },

    "groundnut": {
        "display":    "Groundnut",
        "display_te": "వేరుసెనగ",
        "emoji":      "🥜",
        "desc":       "Prefers well-drained sandy loam, neutral pH, moderate fertility.",
        "rules": [
            ("pH",  6.0, 7.5, 5.5, 8.0, 3,
             "Alkaline soil causes Ca deficiency in groundnut pods",
             "Acidic soil reduces groundnut nodulation and pod fill"),
            ("EC",  0.0, 2.0, 0.0, 3.5, 3,
             "Salinity reduces groundnut germination, peg formation and pod yield",
             None),
            ("OC",  0.4, 2.5, 0.25, 2.5, 1,
             None,
             "Low OC reduces soil moisture retention for groundnut"),
            ("P",   11,  50,  5,   80,   2,
             None,
             "Low phosphorus limits root nodule formation in groundnut"),
            ("Zn",  0.6, 3.0, 0.3, 3.0, 1,
             None,
             "Zinc deficiency causes rosette symptoms in groundnut"),
        ],
    },

    "red_gram": {
        "display":    "Red Gram",
        "display_te": "కందులు",
        "emoji":      "🫘",
        "desc":       "Drought-tolerant dryland crop; fixes nitrogen; suits poor soils.",
        "rules": [
            ("pH",  6.0, 7.5, 5.0, 8.5, 2,
             "High pH limits micronutrient availability for red gram",
             "Acidic soil inhibits rhizobial activity in red gram"),
            ("EC",  0.0, 2.5, 0.0, 4.5, 2,
             "Prolonged salinity reduces red gram flowering and pod set",
             None),
            ("OC",  0.3, 2.5, 0.2, 2.5, 1,
             None,
             "Very low OC — even red gram benefits from baseline organic matter"),
            ("P",   11,  50,  5,   80,   2,
             None,
             "Low P limits root development and nitrogen fixation in red gram"),
            ("N",   80,  420, 40,  560,  1,
             "Excess N suppresses nodule formation — red gram fixes its own N",
             None),
        ],
    },
}

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _score_param(
    value: float,
    opt_lo: float, opt_hi: float,
    marg_lo: float, marg_hi: float,
) -> float:
    """Return a 0.0–1.0 score for a single parameter value."""
    if opt_lo <= value <= opt_hi:
        return 1.0

    if marg_lo <= value < opt_lo:
        span = opt_lo - marg_lo
        return 0.5 + 0.5 * (value - marg_lo) / span if span > 0 else 0.5

    if opt_hi < value <= marg_hi:
        span = marg_hi - opt_hi
        return 0.5 + 0.5 * (marg_hi - value) / span if span > 0 else 0.5

    # Outside marginal — steep penalty
    if value < marg_lo:
        gap = marg_lo - value
        return max(0.0, 0.5 - 0.5 * gap / max(marg_lo, 1))

    gap = value - marg_hi
    return max(0.0, 0.5 - 0.5 * gap / max(marg_hi, 1))


def _grade(score: int) -> tuple[str, str]:
    if score >= 85: return "highly_suitable", "Highly Suitable"
    if score >= 65: return "suitable",        "Suitable"
    if score >= 45: return "marginal",        "Marginal"
    return "unsuitable", "Not Suitable"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_crop(soil: dict[str, float], crop: str) -> dict:
    """Return suitability dict for one crop given a soil measurement dict."""
    profile = PROFILES[crop]
    rules   = profile["rules"]

    total_weight = sum(r[5] for r in rules)
    weighted_sum = 0.0
    constraints: list[str] = []
    strengths:   list[str] = []

    for param, opt_lo, opt_hi, marg_lo, marg_hi, weight, msg_hi, msg_lo in rules:
        val = soil.get(param)
        if val is None:
            # Missing parameter — assume marginal (0.5)
            weighted_sum += 0.5 * weight
            continue

        raw = _score_param(val, opt_lo, opt_hi, marg_lo, marg_hi)
        weighted_sum += raw * weight

        if raw == 1.0:
            strengths.append(f"{param} is in the optimal range")
        elif raw >= 0.7:
            pass  # acceptable, no message
        elif raw >= 0.5:
            if val > opt_hi and msg_hi:
                constraints.append(msg_hi)
            elif val < opt_lo and msg_lo:
                constraints.append(msg_lo)
        else:
            if val > opt_hi and msg_hi:
                constraints.append(msg_hi)
            elif val < opt_lo and msg_lo:
                constraints.append(msg_lo)
            else:
                constraints.append(f"{param} is outside the suitable range for {profile['display']}")

    score = round((weighted_sum / total_weight) * 100)
    grade_key, grade_label = _grade(score)

    return {
        "crop":        crop,
        "display":     profile["display"],
        "display_te":  profile["display_te"],
        "emoji":       profile["emoji"],
        "desc":        profile["desc"],
        "score":       score,
        "grade":       grade_key,
        "grade_label": grade_label,
        "constraints": constraints[:3],   # cap at 3 to keep UI readable
        "strengths":   strengths[:2],
    }


def rank_crops(soil: dict[str, float]) -> dict:
    """Rank all four crops by suitability and return advisory summary."""
    rankings = sorted(
        [score_crop(soil, c) for c in PROFILES],
        key=lambda x: x["score"],
        reverse=True,
    )

    top = rankings[0]

    # Build a plain-language summary
    unsuitable = [r for r in rankings if r["grade"] == "unsuitable"]
    risky_ec   = soil.get("EC", 0) > 2.0

    if risky_ec:
        ec_warning = (
            f"Your soil has elevated salinity (EC {soil['EC']:.1f} dS/m). "
            f"Salt-sensitive crops like paddy will face significant yield loss."
        )
    else:
        ec_warning = None

    summary = (
        f"Your soil best suits {top['display']} this season "
        f"(score {top['score']}/100)."
    )
    if unsuitable:
        names = ", ".join(r["display"] for r in unsuitable)
        summary += f" {names} {'is' if len(unsuitable)==1 else 'are'} not recommended given current soil conditions."

    return {
        "rankings":   rankings,
        "top_pick":   top["crop"],
        "summary":    summary,
        "ec_warning": ec_warning,
    }
