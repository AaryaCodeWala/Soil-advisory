"""
ICAR Fertilizer Recommendation Tables — Andhra Pradesh
=======================================================
All values sourced from ICAR-published guidelines for AP soils.
Never hardcode values elsewhere — always import from here.

Nutrient balance method:
  Dose (kg/ha) = (Crop Requirement - Soil Supply) / Fertilizer Use Efficiency

  Crop Requirement = Target Yield (t/ha) × Nutrient Uptake per tonne of yield
  Soil Supply      = Available nutrient (kg/ha) from soil test value
  FUE              = fraction of applied nutrient taken up by crop
"""

# ---------------------------------------------------------------------------
# Soil test interpretation thresholds (ICAR / APSAC norms for AP soils)
# ---------------------------------------------------------------------------

SOIL_THRESHOLDS = {
    "pH": {
        "strongly_acid":    (0.0, 5.5),
        "moderately_acid":  (5.5, 6.5),
        "optimal":          (6.5, 7.5),
        "mildly_alkaline":  (7.5, 8.5),
        "strongly_alkaline":(8.5, 14.0),
    },
    "EC": {   # dS/m — electrical conductivity
        "normal":   (0.0, 1.0),
        "marginal": (1.0, 2.0),
        "saline":   (2.0, 4.0),
        "highly_saline": (4.0, 99.0),
    },
    "OC": {   # % organic carbon (Walkley-Black method)
        "low":    (0.0,  0.50),
        "medium": (0.50, 0.75),
        "high":   (0.75, 99.0),
    },
    "N": {    # kg/ha available N (alkaline KMnO4 method)
        "low":    (0,   280),
        "medium": (280, 560),
        "high":   (560, 9999),
    },
    "P": {    # kg/ha available P2O5 (Olsen / Bray method)
        "low":    (0,  11),
        "medium": (11, 22),
        "high":   (22, 9999),
    },
    "K": {    # kg/ha available K2O (neutral NH4OAc)
        "low":    (0,   110),
        "medium": (110, 280),
        "high":   (280, 9999),
    },
    "Fe": {   # ppm DTPA-extractable iron
        "deficient": (0.0,  4.5),
        "adequate":  (4.5, 99.0),
    },
    "Cu": {   # ppm DTPA-extractable copper
        "deficient": (0.0, 0.2),
        "adequate":  (0.2, 99.0),
    },
    "B": {    # ppm hot-water soluble boron
        "deficient": (0.0, 0.5),
        "adequate":  (0.5, 99.0),
    },
    "Zn": {   # ppm DTPA-extractable zinc
        "deficient": (0.0, 0.6),
        "adequate":  (0.6, 99.0),
    },
    "S": {    # ppm available sulphur
        "deficient": (0.0, 10.0),
        "adequate":  (10.0, 99.0),
    },
}

# ---------------------------------------------------------------------------
# Fertilizer use efficiency (fraction of applied nutrient used by crop)
# ---------------------------------------------------------------------------

FERTILIZER_USE_EFFICIENCY = {
    "N": 0.30,   # typical for AP flooded paddy; 0.35-0.40 for upland crops
    "P": 0.20,   # P fixation is high in AP red/black soils
    "K": 0.40,
    "Fe": 0.10,
    "Zn": 0.15,
    "B":  0.20,
    "Cu": 0.15,
    "S":  0.25,
}

# ---------------------------------------------------------------------------
# Crop nutrient uptake per tonne of economic yield (kg nutrient / t yield)
# ---------------------------------------------------------------------------

NUTRIENT_UPTAKE_PER_TONNE = {
    "paddy": {
        "N": 23.0, "P": 5.0,  "K": 22.0,
        "Fe": 0.5, "Zn": 0.03, "Cu": 0.004, "B": 0.006, "S": 1.5,
    },
    "cotton": {   # per tonne seed cotton
        "N": 60.0, "P": 20.0, "K": 60.0,
        "Fe": 1.2, "Zn": 0.06, "Cu": 0.01, "B": 0.05, "S": 6.0,
    },
    "groundnut": {   # per tonne pod yield
        "N": 55.0, "P": 6.0, "K": 19.0,
        "Fe": 2.0, "Zn": 0.05, "Cu": 0.01, "B": 0.03, "S": 5.0,
    },
    "red_gram": {   # per tonne grain yield
        "N": 50.0, "P": 8.0,  "K": 20.0,
        "Fe": 1.0, "Zn": 0.04, "Cu": 0.008, "B": 0.02, "S": 3.0,
    },
}

# ---------------------------------------------------------------------------
# Soil nutrient supply factors (kg available nutrient / unit soil test value)
# Used to convert soil test reading → kg/ha supply
# ---------------------------------------------------------------------------

SOIL_SUPPLY_FACTORS = {
    "N":  1.0,   # soil test already in kg/ha
    "P":  1.0,   # soil test already in kg/ha P2O5
    "K":  1.0,   # soil test already in kg/ha K2O
    "Fe": 2.0,   # ppm → kg/ha approximation
    "Zn": 1.5,
    "Cu": 1.0,
    "B":  0.8,
    "S":  1.2,
}

# ---------------------------------------------------------------------------
# Target yields (t/ha) used when farmer doesn't specify
# ---------------------------------------------------------------------------

DEFAULT_TARGET_YIELD = {
    "paddy":     5.5,   # t/ha, progressive farmer yield for AP
    "cotton":    2.2,   # t/ha seed cotton
    "groundnut": 2.0,   # t/ha pods
    "red_gram":  1.5,   # t/ha grain
}

# ---------------------------------------------------------------------------
# Fertilizer application schedules (basal + split doses)
# Values are fractions of total dose
# ---------------------------------------------------------------------------

APPLICATION_SCHEDULE = {
    "paddy": {
        "N": [
            {"timing": "Basal (transplanting)",         "fraction": 0.333},
            {"timing": "Top dress 1 (21 DAT, tillering)","fraction": 0.333},
            {"timing": "Top dress 2 (45 DAT, panicle)", "fraction": 0.333},
        ],
        "P": [{"timing": "Basal", "fraction": 1.0}],
        "K": [
            {"timing": "Basal",                         "fraction": 0.50},
            {"timing": "Top dress 1 (21 DAT)",          "fraction": 0.50},
        ],
    },
    "cotton": {
        "N": [
            {"timing": "Basal",                         "fraction": 0.25},
            {"timing": "Top dress 1 (30 DAS)",          "fraction": 0.25},
            {"timing": "Top dress 2 (60 DAS)",          "fraction": 0.25},
            {"timing": "Top dress 3 (90 DAS)",          "fraction": 0.25},
        ],
        "P": [{"timing": "Basal", "fraction": 1.0}],
        "K": [
            {"timing": "Basal",                         "fraction": 0.50},
            {"timing": "Top dress 1 (60 DAS)",          "fraction": 0.50},
        ],
    },
    "groundnut": {
        "N": [{"timing": "Basal (starter N)",           "fraction": 1.0}],
        "P": [{"timing": "Basal",                       "fraction": 1.0}],
        "K": [{"timing": "Basal",                       "fraction": 1.0}],
    },
    "red_gram": {
        "N": [{"timing": "Basal (starter N)",           "fraction": 1.0}],
        "P": [{"timing": "Basal",                       "fraction": 1.0}],
        "K": [{"timing": "Basal",                       "fraction": 1.0}],
    },
}

# ---------------------------------------------------------------------------
# Micronutrient correction doses (kg/ha of carrier material)
# Applied when soil test shows deficiency
# ---------------------------------------------------------------------------

MICRONUTRIENT_CORRECTIONS = {
    "Zn": {
        "carrier": "Zinc Sulphate (ZnSO₄·7H₂O, 21% Zn)",
        "dose_kg_ha": 25,
        "timing": "Basal",
        "crops": ["paddy", "cotton", "groundnut", "red_gram"],
        "foliar_dose": "0.5% ZnSO₄ spray at 30 and 45 DAS",
    },
    "Fe": {
        "carrier": "Ferrous Sulphate (FeSO₄·7H₂O, 19% Fe)",
        "dose_kg_ha": 25,
        "timing": "Basal",
        "crops": ["paddy", "groundnut", "red_gram"],
        "foliar_dose": "1% FeSO₄ + 0.5% citric acid spray (2-3 sprays)",
    },
    "B": {
        "carrier": "Borax (Na₂B₄O₇·10H₂O, 11% B)",
        "dose_kg_ha": 10,
        "timing": "Basal",
        "crops": ["cotton", "groundnut"],
        "foliar_dose": "0.2% borax spray at flowering",
    },
    "Cu": {
        "carrier": "Copper Sulphate (CuSO₄·5H₂O, 25% Cu)",
        "dose_kg_ha": 5,
        "timing": "Basal (once every 3 years)",
        "crops": ["paddy", "cotton", "groundnut", "red_gram"],
        "foliar_dose": "0.2% CuSO₄ spray",
    },
    "S": {
        "carrier": "Gypsum (CaSO₄·2H₂O, 18% S)",
        "dose_kg_ha": {"groundnut": 400, "cotton": 200, "paddy": 100, "red_gram": 150},
        "timing": "Basal at pegging (groundnut) / sowing",
        "crops": ["groundnut", "cotton", "paddy", "red_gram"],
    },
}

# ---------------------------------------------------------------------------
# Common fertilizer material composition (% nutrient content)
# ---------------------------------------------------------------------------

FERTILIZER_MATERIALS = {
    "Urea":                 {"N": 0.46},
    "DAP":                  {"N": 0.18, "P2O5": 0.46},
    "SSP":                  {"P2O5": 0.16, "S": 0.12, "Ca": 0.21},
    "MOP":                  {"K2O": 0.60},
    "NPK 14:35:14":         {"N": 0.14, "P2O5": 0.35, "K2O": 0.14},
    "NPK 17:17:17":         {"N": 0.17, "P2O5": 0.17, "K2O": 0.17},
    "Ammonium Sulphate":    {"N": 0.21, "S": 0.24},
    "ZnSO4 (Zinc Sulphate)":{"Zn": 0.21},
    "FeSO4 (Ferrous Sulphate)": {"Fe": 0.19},
    "Borax":                {"B": 0.11},
    "Gypsum":               {"S": 0.18, "Ca": 0.23},
}

# ---------------------------------------------------------------------------
# Fertilizer price (₹/kg) — AP market rates, May 2025
# ---------------------------------------------------------------------------

FERTILIZER_PRICES_PER_KG = {
    "Urea":             6.5,
    "DAP":             27.0,
    "SSP":              8.0,
    "MOP":             17.0,
    "ZnSO4":           55.0,
    "FeSO4":           30.0,
    "Borax":           80.0,
    "Gypsum":           4.5,
}

# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------

def compute_dose(
    crop: str,
    nutrient: str,
    soil_test_value: float,
    target_yield: float | None = None,
) -> dict:
    """
    Compute fertilizer dose for a single crop × nutrient combination.

    Returns a dict with:
        dose_kg_ha      — nutrient element dose
        soil_supply     — estimated soil supply (kg/ha)
        crop_requirement — total crop requirement (kg/ha)
        schedule        — list of split applications
    """
    if target_yield is None:
        target_yield = DEFAULT_TARGET_YIELD[crop]

    uptake   = NUTRIENT_UPTAKE_PER_TONNE[crop][nutrient]
    fue      = FERTILIZER_USE_EFFICIENCY[nutrient]
    sf       = SOIL_SUPPLY_FACTORS[nutrient]

    crop_req  = uptake * target_yield
    soil_sup  = soil_test_value * sf
    net_req   = max(0.0, crop_req - soil_sup)
    dose      = net_req / fue

    schedule = APPLICATION_SCHEDULE.get(crop, {}).get(nutrient, [
        {"timing": "Basal", "fraction": 1.0}
    ])

    splits = [
        {
            "timing":       s["timing"],
            "dose_kg_ha":   round(dose * s["fraction"], 1),
        }
        for s in schedule
    ]

    return {
        "crop":             crop,
        "nutrient":         nutrient,
        "target_yield_t_ha":target_yield,
        "crop_requirement": round(crop_req, 1),
        "soil_supply":      round(soil_sup, 1),
        "net_requirement":  round(net_req, 1),
        "dose_kg_ha":       round(dose, 1),
        "splits":           splits,
    }


def full_recommendation(
    crop: str,
    soil: dict,
    target_yield: float | None = None,
    area_acres: float = 1.0,
) -> dict:
    """
    Generate a complete fertilizer schedule for a field.

    Args:
        crop:         one of paddy / cotton / groundnut / red_gram
        soil:         dict of soil test values {pH, EC, OC, N, P, K, Fe, Cu, B, Zn, S}
        target_yield: t/ha (optional, uses default if None)
        area_acres:   field area in acres for quantity calculations

    Returns:
        Full recommendation dict including macronutrients, micronutrients,
        schedule, and estimated cost.
    """
    if crop not in DEFAULT_TARGET_YIELD:
        raise ValueError(f"Unknown crop: {crop}. Must be one of {list(DEFAULT_TARGET_YIELD)}")

    ha = area_acres * 0.4047
    recs = {}

    for nutrient in ["N", "P", "K"]:
        if nutrient in soil:
            recs[nutrient] = compute_dose(crop, nutrient, soil[nutrient], target_yield)

    # Micronutrient corrections
    micro_recs = []
    for nutrient, correction in MICRONUTRIENT_CORRECTIONS.items():
        if nutrient not in soil:
            continue
        if crop not in correction["crops"]:
            continue
        threshold = SOIL_THRESHOLDS.get(nutrient, {}).get("deficient", (0, 0))
        if soil[nutrient] < threshold[1]:
            dose = correction["dose_kg_ha"]
            if isinstance(dose, dict):
                dose = dose.get(crop, 0)
            micro_recs.append({
                "nutrient":   nutrient,
                "carrier":    correction["carrier"],
                "dose_kg_ha": dose,
                "dose_kg_acre": round(dose * 0.4047, 1),
                "timing":     correction["timing"],
                "foliar":     correction.get("foliar_dose"),
            })

    # Estimate cost saving vs blanket application
    # Blanket norm: fixed N=120, P=60, K=60 kg/ha for all fields
    blanket_cost = (120 / 0.46 * 6.5 + 60 / 0.46 * 27 + 60 / 0.6 * 17) * ha
    actual_n = recs.get("N", {}).get("dose_kg_ha", 120)
    actual_p = recs.get("P", {}).get("dose_kg_ha", 60)
    actual_k = recs.get("K", {}).get("dose_kg_ha", 60)
    actual_cost = (actual_n / 0.46 * 6.5 + actual_p / 0.46 * 27 + actual_k / 0.6 * 17) * ha
    savings = max(0, blanket_cost - actual_cost)

    return {
        "crop":               crop,
        "area_acres":         area_acres,
        "target_yield_t_ha":  target_yield or DEFAULT_TARGET_YIELD[crop],
        "macronutrients":     recs,
        "micronutrients":     micro_recs,
        "estimated_savings_inr": round(savings, 0),
    }
