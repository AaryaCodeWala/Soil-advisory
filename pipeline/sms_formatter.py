"""
SMS Formatter — Fertilizer Recommendations
===========================================
Converts full_recommendation() output into compact SMS messages for feature phones.

Encoding rules observed:
  English  — GSM-7 (160 chars/segment, 153 in multi-part)
  Telugu   — UCS-2 (70 chars/segment, 67 in multi-part)

Two verbosity modes:
  "short"  — 1-2 segments; NPK totals only, no split schedule
  "full"   — 2-3 segments; includes basal/split-dose breakdown
"""

from __future__ import annotations
from typing import Literal

# ---------------------------------------------------------------------------
# Crop / nutrient labels
# ---------------------------------------------------------------------------

_CROP_EN = {
    "paddy":     "Paddy",
    "cotton":    "Cotton",
    "groundnut": "Groundnut",
    "red_gram":  "Red Gram",
}
_CROP_TE = {
    "paddy":     "వరి",
    "cotton":    "పత్తి",
    "groundnut": "వేరుసెనగ",
    "red_gram":  "కందులు",
}
_NUTRIENT_TE = {
    "N":  "నత్రజని",
    "P":  "భాస్వరం",
    "K":  "పొటాషియం",
    "Zn": "జింక్",
    "Fe": "ఇనుము",
    "B":  "బోరాన్",
    "Cu": "రాగి",
    "S":  "గంధకం",
}

# Timing abbreviations for Telugu (keep short to save chars)
_TIMING_TE = {
    "Basal":                              "విత్తన సమయంలో",
    "Basal (transplanting)":              "నాటు వేసేటప్పుడు",
    "Basal (starter N)":                  "విత్తన సమయంలో",
    "Top dress 1 (21 DAT, tillering)":    "21వ రోజు",
    "Top dress 2 (45 DAT, panicle)":      "45వ రోజు",
    "Top dress 1 (21 DAT)":               "21వ రోజు",
    "Top dress 1 (30 DAS)":               "30వ రోజు",
    "Top dress 2 (60 DAS)":               "60వ రోజు",
    "Top dress 3 (90 DAS)":               "90వ రోజు",
    "Top dress 1 (60 DAS)":               "60వ రోజు",
}

# ---------------------------------------------------------------------------
# GSM-7 character detection
# ---------------------------------------------------------------------------

# Standard GSM-7 table (Basic Character Set)
_GSM7 = set(
    "@£$¥èéùìòÇ\nØø\rÅå\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "ÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyz"
    "äöñüà"
    # Extended table chars that count as 2 GSM-7 chars each (simplified: treat as 2)
    # We ignore extension for segment counting purposes and treat them as 1
    "^{}\\[~]|€"
)


def _is_gsm7(text: str) -> bool:
    return all(c in _GSM7 for c in text)


def sms_segments(text: str) -> int:
    """Return number of SMS segments needed to transmit text."""
    unicode_mode = not _is_gsm7(text)
    single = 70  if unicode_mode else 160
    multi  = 67  if unicode_mode else 153
    n = len(text)
    if n <= single:
        return 1
    return -(-n // multi)  # ceiling division


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _per_acre(kg_ha: float) -> float:
    return round(kg_ha * 0.4047, 1)


def _timing_abbrev_en(timing: str) -> str:
    """Shorten English timing string for SMS."""
    timing = timing.split("(")[0].strip()
    return timing.replace("Top dress", "TD").replace("Basal", "Basal")


# ---------------------------------------------------------------------------
# English formatter
# ---------------------------------------------------------------------------

def format_english(
    rec: dict,
    farmer_name: str = "",
    mode: Literal["short", "full"] = "short",
) -> str:
    crop    = _CROP_EN.get(rec["crop"], rec["crop"].title())
    area    = rec["area_acres"]
    yield_t = rec["target_yield_t_ha"]
    macros  = rec["macronutrients"]
    micros  = rec["micronutrients"]
    savings = int(rec["estimated_savings_inr"])

    n_ac = _per_acre(macros["N"]["dose_kg_ha"]) if "N" in macros else 0
    p_ac = _per_acre(macros["P"]["dose_kg_ha"]) if "P" in macros else 0
    k_ac = _per_acre(macros["K"]["dose_kg_ha"]) if "K" in macros else 0

    # Header — stay ASCII/GSM-7 (avoid Rs. symbol if using rupee sign)
    hdr = "[AP Ag Dept] SOIL ADVISORY"
    if farmer_name:
        hdr += f" - {farmer_name}"

    field = f"Crop:{crop} {area}ac Target:{yield_t}t/ha"

    def _fmt(v: float) -> str:
        return "OK" if v == 0.0 else f"{v}kg/ac"

    if mode == "short":
        npk = f"Apply: N={_fmt(n_ac)} P={_fmt(p_ac)} K={_fmt(k_ac)}"
    else:
        lines = ["NPK schedule (kg/acre):"]
        for nut in ["N", "P", "K"]:
            if nut not in macros:
                continue
            for sp in macros[nut]["splits"]:
                dose = _per_acre(sp["dose_kg_ha"])
                if dose == 0.0:
                    continue
                t = _timing_abbrev_en(sp["timing"])
                lines.append(f"  {nut} {t}: {dose}")
        if len(lines) == 1:
            lines.append("  No macro application needed.")
        npk = "\n".join(lines)

    if micros:
        items = [f"{m['nutrient']}({m['dose_kg_acre']}kg/ac)" for m in micros]
        micro = "Deficient: " + ", ".join(items) + " - apply basal"
    else:
        micro = "No micronutrient deficiency."

    save  = f"Savings vs blanket: Rs.{savings}"
    foot  = "Helpline: 1800-425-2910"

    return "\n".join([hdr, field, npk, micro, save, foot])


# ---------------------------------------------------------------------------
# Telugu formatter
# ---------------------------------------------------------------------------

def format_telugu(
    rec: dict,
    farmer_name: str = "",
    mode: Literal["short", "full"] = "short",
) -> str:
    crop_te = _CROP_TE.get(rec["crop"], rec["crop"])
    area    = rec["area_acres"]
    yield_t = rec["target_yield_t_ha"]
    macros  = rec["macronutrients"]
    micros  = rec["micronutrients"]
    savings = int(rec["estimated_savings_inr"])

    n_ac = _per_acre(macros["N"]["dose_kg_ha"]) if "N" in macros else 0
    p_ac = _per_acre(macros["P"]["dose_kg_ha"]) if "P" in macros else 0
    k_ac = _per_acre(macros["K"]["dose_kg_ha"]) if "K" in macros else 0

    hdr   = "[AP వ్యవసాయ శాఖ] మట్టి సలహా"
    if farmer_name:
        hdr += f" - {farmer_name}"

    field = f"పంట:{crop_te} {area}ఎ | లక్ష్యం:{yield_t}t"

    def _fmt_te(v: float) -> str:
        return "సరి" if v == 0.0 else f"{v}kg/ఎ"

    if mode == "short":
        npk = f"వేయండి: N={_fmt_te(n_ac)} P={_fmt_te(p_ac)} K={_fmt_te(k_ac)}"
    else:
        lines = ["NPK సమయపట్టిక (kg/ఎ):"]
        for nut in ["N", "P", "K"]:
            if nut not in macros:
                continue
            for sp in macros[nut]["splits"]:
                dose = _per_acre(sp["dose_kg_ha"])
                if dose == 0.0:
                    continue
                t = _TIMING_TE.get(sp["timing"], sp["timing"])
                lines.append(f"  {nut} {t}: {dose}")
        if len(lines) == 1:
            lines.append("  స్థూల పోషకాలు అవసరం లేదు.")
        npk = "\n".join(lines)

    if micros:
        names = [_NUTRIENT_TE.get(m["nutrient"], m["nutrient"]) for m in micros]
        micro = "లోపం: " + ", ".join(names) + " - మూల వేత వేయండి"
    else:
        micro = "సూక్ష్మ పోషక లోపాలు లేవు."

    save = f"ఆదా: ₹{savings}"  # ₹
    foot = "సహాయం: 1800-425-2910"

    return "\n".join([hdr, field, npk, micro, save, foot])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def format_sms(
    rec: dict,
    lang: Literal["en", "te", "both"] = "both",
    farmer_name: str = "",
    mode: Literal["short", "full"] = "short",
) -> dict:
    """
    Format a full_recommendation() result into SMS messages.

    Returns a dict with keys:
        en, en_segs   — English text and segment count  (if lang in ["en","both"])
        te, te_segs   — Telugu  text and segment count  (if lang in ["te","both"])
    """
    result: dict = {}
    if lang in ("en", "both"):
        en = format_english(rec, farmer_name=farmer_name, mode=mode)
        result["en"]      = en
        result["en_segs"] = sms_segments(en)
        result["en_chars"] = len(en)
    if lang in ("te", "both"):
        te = format_telugu(rec, farmer_name=farmer_name, mode=mode)
        result["te"]      = te
        result["te_segs"] = sms_segments(te)
        result["te_chars"] = len(te)
    return result


# ---------------------------------------------------------------------------
# CLI smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from fertilizer_tables import full_recommendation

    sample = {
        "pH": 6.8, "EC": 0.45, "OC": 0.52,
        "N": 210, "P": 14, "K": 145,
        "Fe": 3.2, "Zn": 0.3, "B": 0.8, "Cu": 0.25,
    }
    rec = full_recommendation("paddy", sample, area_acres=2.5)
    msgs = format_sms(rec, lang="both", farmer_name="Ravi Reddy", mode="short")

    print("=== ENGLISH SMS (short) ===")
    print(msgs["en"])
    print(f"Chars: {msgs['en_chars']}  |  Segments: {msgs['en_segs']}\n")

    print("=== TELUGU SMS (short) ===")
    print(msgs["te"])
    print(f"Chars: {msgs['te_chars']}  |  Segments: {msgs['te_segs']}\n")

    msgs_full = format_sms(rec, lang="both", farmer_name="Ravi Reddy", mode="full")
    print("=== ENGLISH SMS (full) ===")
    print(msgs_full["en"])
    print(f"Chars: {msgs_full['en_chars']}  |  Segments: {msgs_full['en_segs']}\n")

    print("=== TELUGU SMS (full) ===")
    print(msgs_full["te"])
    print(f"Chars: {msgs_full['te_chars']}  |  Segments: {msgs_full['te_segs']}")
