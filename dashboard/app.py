"""
Soil Nutrient Mapping Dashboard — Plotly Dash
Run: python dashboard/app.py
"""

import os
import sys
import functools
from pathlib import Path

import numpy as np
import pandas as pd

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import transform as warp_transform

sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))
from fertilizer_tables import full_recommendation, SOIL_THRESHOLDS, DEFAULT_TARGET_YIELD
from config import PROCESSED_DIR, SOIL_PARAMS

MAPS_DIR = PROCESSED_DIR / "maps"
WINDOW = "post_kharif_2024"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PARAM_LABELS = {
    "pH": "Soil pH",        "EC": "EC (dS/m)",
    "OC": "Organic Carbon (%)", "N": "Available N (kg/ha)",
    "P":  "Available P (kg/ha)", "K": "Available K (kg/ha)",
    "Fe": "Iron (ppm)",     "Cu": "Copper (ppm)",
    "B":  "Boron (ppm)",    "Zn": "Zinc (ppm)",
}
PARAM_UNITS = {
    "pH": "", "EC": "dS/m", "OC": "%",
    "N": "kg/ha", "P": "kg/ha", "K": "kg/ha",
    "Fe": "ppm", "Cu": "ppm", "B": "ppm", "Zn": "ppm",
}
CROPS = {
    "paddy":     "Paddy (వరి)",
    "cotton":    "Cotton (పత్తి)",
    "groundnut": "Groundnut (వేరుసెనగ)",
    "red_gram":  "Red Gram (కందులు)",
}
CROPS_TE = {
    "paddy":     "వరి",
    "cotton":    "పత్తి",
    "groundnut": "వేరుసెనగ",
    "red_gram":  "కందులు",
}
# Telugu UI strings (ISO 639-1: te)
TELUGU = {
    "field_details":  "పొలం వివరాలు",
    "gen_btn":        "సిఫార్సు పొందండి",
    "npk_schedule":   "NPK వేసే సమయపట్టిక",
    "micro_correct":  "సూక్ష్మ పోషక దిద్దుబాట్లు",
    "no_micro":       "సూక్ష్మ పోషక లోపాలు లేవు.",
    "no_macro":       "పోషక స్థాయిలు తగినవి — స్థూల పోషక దరఖాస్తు అవసరం లేదు.",
    "savings_txt":    "అంచనా ఆదా — మొత్తం దరఖాస్తుతో పోలిస్తే",
    "col_nutrient":   "పోషకం",
    "col_timing":     "సమయం",
    "col_kg_ha":      "kg/హెక్టారు",
    "col_kg_acre":    "kg/ఎకరం",
    "deficiency":     "లోపం",
    "apply":          "వేయండి",
    "acres":          "ఎకరాలు",
    "target":         "లక్ష్యం",
}
GREEN = "#2e7d32"
AMBER = "#e65100"

# ---------------------------------------------------------------------------
# Data loading  (None-results are NOT cached so maps are picked up on next call)
# ---------------------------------------------------------------------------

_data_cache: dict = {}

def load_param_data(param: str, n_samples: int = 4000) -> pd.DataFrame | None:
    if param in _data_cache:
        return _data_cache[param]

    pred_path = MAPS_DIR / f"{param}_{WINDOW}_prediction.tif"
    conf_path = MAPS_DIR / f"{param}_{WINDOW}_confidence.tif"
    if not pred_path.exists():
        return None

    TARGET = 500
    with rasterio.open(pred_path) as src:
        H, W   = src.height, src.width
        sh, sw = min(TARGET, H), min(TARGET, W)
        data   = src.read(1, out_shape=(sh, sw), resampling=Resampling.average).astype(np.float32)
        bounds = src.bounds
        crs    = src.crs

    with rasterio.open(conf_path) as src:
        conf = src.read(1, out_shape=(sh, sw), resampling=Resampling.average).astype(np.float32)

    valid = ~np.isnan(data)
    if not valid.any():
        return None

    lon_grid = np.linspace(bounds.left,  bounds.right,  sw)
    lat_grid = np.linspace(bounds.top,   bounds.bottom, sh)
    lons_utm, lats_utm = np.meshgrid(lon_grid, lat_grid)

    flat_lons = lons_utm[valid].flatten()
    flat_lats = lats_utm[valid].flatten()
    lons_wgs, lats_wgs = warp_transform(crs, "EPSG:4326", flat_lons, flat_lats)

    df = pd.DataFrame({
        "lat":        np.array(lats_wgs, dtype=np.float32),
        "lon":        np.array(lons_wgs, dtype=np.float32),
        "value":      data[valid].flatten(),
        "confidence": conf[valid].flatten(),
    })
    if len(df) > n_samples:
        df = df.sample(n_samples, random_state=42).reset_index(drop=True)

    _data_cache[param] = df
    return df


def get_map_stats() -> dict:
    stats = {}
    for param in SOIL_PARAMS:
        df = load_param_data(param)
        if df is None:
            continue
        first_range = list(SOIL_THRESHOLDS.get(param, {}).values())
        low_thresh  = first_range[0][1] if first_range else float(np.nanpercentile(df["value"], 25))
        stats[param] = {
            "mean":     float(np.nanmean(df["value"])),
            "avg_conf": float(np.nanmean(df["confidence"])),
            "pct_low":  float(np.mean(df["value"] < low_thresh) * 100),
        }
    return stats

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
    title="Soil Health Intelligence — AP",
    suppress_callback_exceptions=True,
)

# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------

def make_navbar():
    return dbc.Navbar(
        dbc.Container([
            html.Span([
                html.I(className="bi bi-geo-alt-fill me-2"),
                dbc.NavbarBrand("Soil Health Intelligence", className="fw-bold fs-5"),
            ]),
            dbc.Nav([
                dbc.NavItem(html.Span("Krishna District Pilot", className="navbar-text text-white-50 me-3 small")),
                dbc.NavItem(html.Span("Kharif 2024 | Sentinel-2 L2A + SHC", className="navbar-text text-white-50 small")),
            ], className="ms-auto", navbar=True),
        ], fluid=True),
        color=GREEN, dark=True, className="mb-4 shadow-sm",
    )


def make_officials_tab():
    return html.Div([
        dcc.Interval(id="stats-interval", interval=30_000, n_intervals=0),
        html.Div(id="kpi-row", className="mb-4"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.Strong("Map Controls")),
                    dbc.CardBody([
                        html.Label("Parameter", className="fw-semibold small"),
                        dcc.Dropdown(
                            id="param-select",
                            options=[{"label": PARAM_LABELS[p], "value": p} for p in SOIL_PARAMS],
                            value="pH", clearable=False, className="mb-3",
                        ),
                        html.Label("Colour by", className="fw-semibold small"),
                        dbc.RadioItems(
                            id="layer-select",
                            options=[
                                {"label": "Predicted Value",  "value": "value"},
                                {"label": "Confidence Score", "value": "confidence"},
                            ],
                            value="value", className="mb-3",
                        ),
                        html.Hr(className="my-2"),
                        html.Div(id="stats-panel"),
                    ]),
                ], className="shadow-sm"),
            ], md=3),

            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.Strong("Soil Parameter Map — Krishna District")),
                    dbc.CardBody(
                        dcc.Graph(id="soil-map", style={"height": "460px"},
                                  config={"scrollZoom": True, "displayModeBar": True}),
                        className="p-1",
                    ),
                ], className="shadow-sm"),
            ], md=9),
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.Strong("District Deficiency Overview (% area below low threshold)")),
                    dbc.CardBody(dcc.Graph(id="deficiency-bar", style={"height": "260px"},
                                          config={"displayModeBar": False})),
                ], className="shadow-sm"),
            ], md=8),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.Strong("Confidence Distribution")),
                    dbc.CardBody(dcc.Graph(id="conf-hist", style={"height": "260px"},
                                          config={"displayModeBar": False})),
                ], className="shadow-sm"),
            ], md=4),
        ]),
    ])


def make_farmer_tab():
    return html.Div([
        dbc.Row([
            # ── Inputs ──────────────────────────────────────────────────
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(
                        dbc.Row([
                            dbc.Col([
                                html.I(className="bi bi-person-fill me-2"),
                                html.Strong("Field Details"),
                                html.Span(" / పొలం వివరాలు", className="text-muted ms-1 small"),
                            ], width="auto"),
                            dbc.Col(
                                dbc.RadioItems(
                                    id="lang-toggle",
                                    options=[
                                        {"label": "EN",      "value": "en"},
                                        {"label": "తెలుగు", "value": "te"},
                                    ],
                                    value="en",
                                    inline=True,
                                    className="mb-0",
                                    inputClassName="me-1",
                                ),
                                className="ms-auto d-flex align-items-center",
                            ),
                        ], align="center", className="g-0 flex-nowrap"),
                    ),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label("Crop", className="fw-semibold small"),
                                dcc.Dropdown(
                                    id="crop-select",
                                    options=[{"label": v, "value": k} for k, v in CROPS.items()],
                                    value="paddy", clearable=False,
                                ),
                            ], md=7),
                            dbc.Col([
                                html.Label("Area (acres)", className="fw-semibold small"),
                                dbc.Input(id="area-input", type="number", value=2.0, min=0.5, step=0.5),
                            ], md=5),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                html.Label("Target Yield (t/ha)", className="fw-semibold small"),
                                dbc.Input(id="yield-input", type="number", value=5.5, min=0.5, step=0.5),
                            ], md=6),
                        ], className="mb-3"),

                        html.Hr(className="my-2"),
                        html.P("Macronutrients", className="fw-semibold small mb-2 text-muted text-uppercase"),

                        *[
                            html.Div([
                                html.Label(lbl, className="small"),
                                dcc.Slider(id=sid, min=mn, max=mx, step=st, value=val,
                                           marks={k: str(k) for k in mrks},
                                           tooltip={"placement": "bottom", "always_visible": True}),
                            ], className="mb-3")
                            for sid, lbl, mn, mx, st, val, mrks in [
                                ("sl-ph", "pH",             4.0, 10.0, 0.1, 6.8, [4, 5.5, 6.5, 7.5, 9, 10]),
                                ("sl-ec", "EC (dS/m)",      0.0,  6.0, 0.1, 0.4, [0, 1, 2, 4, 6]),
                                ("sl-oc", "Organic Carbon (%)", 0.0, 2.5, 0.05, 0.45, [0, 0.5, 0.75, 1.5, 2.5]),
                                ("sl-n",  "Available N (kg/ha)", 0, 800, 10, 200, [0, 280, 560, 800]),
                                ("sl-p",  "Available P (kg/ha)", 0,  80,  1,  18, [0, 11, 22, 80]),
                                ("sl-k",  "Available K (kg/ha)", 0, 600, 10, 150, [0, 110, 280, 600]),
                            ]
                        ],

                        html.Hr(className="my-2"),
                        html.P("Micronutrients (ppm, 0 if untested)", className="fw-semibold small mb-2 text-muted text-uppercase"),
                        dbc.Row([
                            dbc.Col([html.Label("Zn", className="small"), dbc.Input(id="inp-zn", type="number", value=0.4, min=0, step=0.1)], md=3),
                            dbc.Col([html.Label("Fe", className="small"), dbc.Input(id="inp-fe", type="number", value=3.5, min=0, step=0.5)], md=3),
                            dbc.Col([html.Label("B",  className="small"), dbc.Input(id="inp-b",  type="number", value=0.3, min=0, step=0.1)], md=3),
                            dbc.Col([html.Label("Cu", className="small"), dbc.Input(id="inp-cu", type="number", value=0.15, min=0, step=0.05)], md=3),
                        ], className="mb-3"),

                        dbc.Button(
                            id="rec-btn", color="success", size="lg", className="w-100 mt-1",
                            children=[html.I(className="bi bi-calculator me-2"), "Generate Recommendation"],
                        ),
                    ]),
                ], className="shadow-sm"),
            ], md=5),

            # ── Output ──────────────────────────────────────────────────
            dbc.Col([
                html.Div(
                    dbc.Alert([
                        html.I(className="bi bi-arrow-left-circle me-2"),
                        "Fill in your field details and click ",
                        html.Strong("Generate Recommendation"),
                    ], color="light", className="border"),
                    id="rec-output",
                ),
            ], md=7),
        ]),
    ])


app.layout = html.Div([
    dcc.Store(id="lang-store", data="en"),
    make_navbar(),
    dbc.Container([
        dbc.Tabs([
            dbc.Tab(make_officials_tab(), label="Officials Dashboard",     tab_id="officials",
                    label_style={"fontWeight": "600"}),
            dbc.Tab(make_farmer_tab(),   label="Farmer Advisory / రైతు సలహా", tab_id="farmer",
                    label_style={"fontWeight": "600"}),
        ], active_tab="officials"),
    ], fluid=True),
], style={"backgroundColor": "#f8f9fa", "minHeight": "100vh"})

# ---------------------------------------------------------------------------
# Callbacks — Officials
# ---------------------------------------------------------------------------

@app.callback(Output("kpi-row", "children"), Input("stats-interval", "n_intervals"))
def refresh_kpis(_):
    stats = get_map_stats()
    if not stats:
        return dbc.Alert([
            html.I(className="bi bi-info-circle me-2"),
            "No prediction maps found yet. Run ",
            html.Code("python pipeline/05_predict_maps.py --all-params"),
            " then this panel will populate automatically.",
        ], color="info")

    cards = []
    for param, s in stats.items():
        conf_color = "success" if s["avg_conf"] > 0.75 else "warning" if s["avg_conf"] > 0.5 else "danger"
        def_color  = "danger"  if s["pct_low"]  > 60    else "warning" if s["pct_low"]  > 30  else "success"
        cards.append(dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    html.P(PARAM_LABELS.get(param, param), className="text-muted mb-1",
                           style={"fontSize": "0.7rem", "fontWeight": 600}),
                    html.H4(f"{s['mean']:.2f}", className="fw-bold mb-1"),
                    dbc.Badge(f"{s['avg_conf']:.0%} conf", color=conf_color, className="me-1"),
                    dbc.Badge(f"{s['pct_low']:.0f}% low",  color=def_color),
                ], className="p-2"),
            ], className="shadow-sm h-100 border-0"),
            xs=6, sm=4, md=2, className="mb-2",
        ))
    return dbc.Row(cards)


@app.callback(
    Output("soil-map",    "figure"),
    Output("stats-panel", "children"),
    Input("param-select", "value"),
    Input("layer-select", "value"),
)
def update_map(param, layer):
    df = load_param_data(param)

    # ── No maps yet ──────────────────────────────────────────────────────────
    if df is None:
        fig = go.Figure()
        fig.add_annotation(
            text="Prediction maps not yet generated.<br>"
                 "<b>python pipeline/05_predict_maps.py --all-params</b>",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=14, color="#666"),
            align="center",
        )
        fig.update_layout(
            mapbox=dict(style="open-street-map", center=dict(lat=16.2, lon=80.7), zoom=7),
            margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="#f8f9fa",
        )
        return fig, html.P("No data yet.", className="text-muted small")

    col   = layer
    label = PARAM_LABELS.get(param, param) if layer == "value" else "Confidence Score"
    unit  = PARAM_UNITS.get(param, "")     if layer == "value" else ""

    invert = param in ("EC",)
    cscale = "RdYlGn_r" if invert else "RdYlGn"

    fig = go.Figure(go.Scattermapbox(
        lat=df["lat"], lon=df["lon"],
        mode="markers",
        marker=dict(
            size=4, opacity=0.75,
            color=df[col], colorscale=cscale, showscale=True,
            colorbar=dict(
                title=dict(text=f"{param}<br>{unit}", side="right"),
                thickness=12, len=0.65, x=1.01,
            ),
        ),
        text=[f"{label}: {v:.3f} {unit}" for v in df[col]],
        hovertemplate="%{text}<extra></extra>",
        name="",
    ))
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=16.6, lon=80.8),
            zoom=9,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        uirevision=param,
        paper_bgcolor="white",
    )

    # Stats panel
    first_range = list(SOIL_THRESHOLDS.get(param, {}).values())
    low_thresh  = first_range[0][1] if first_range else float(np.nanpercentile(df["value"], 25))
    pct_low     = float(np.mean(df["value"] < low_thresh) * 100)

    panel = dbc.ListGroup([
        dbc.ListGroupItem([html.B("Mean: "),       f"{df['value'].mean():.3f} {unit}"],      className="py-1 small border-0"),
        dbc.ListGroupItem([html.B("Std dev: "),    f"{df['value'].std():.3f}"],               className="py-1 small border-0"),
        dbc.ListGroupItem([html.B("Avg conf: "),   f"{df['confidence'].mean():.1%}"],         className="py-1 small border-0"),
        dbc.ListGroupItem([
            html.B("% deficient: "),
            dbc.Badge(f"{pct_low:.1f}%",
                      color="danger" if pct_low > 50 else "warning" if pct_low > 25 else "success"),
        ], className="py-1 small border-0"),
    ], flush=True, className="mt-1")

    return fig, panel


@app.callback(Output("deficiency-bar", "figure"), Input("stats-interval", "n_intervals"))
def update_deficiency_bar(_):
    stats = get_map_stats()
    if not stats:
        fig = go.Figure()
        fig.add_annotation(text="No maps yet", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(color="#aaa"))
        fig.update_layout(margin=dict(l=20, r=20, t=10, b=20), paper_bgcolor="white")
        return fig

    params  = list(stats.keys())
    pct_low = [stats[p]["pct_low"] for p in params]
    colors  = ["#c62828" if v > 60 else "#ef6c00" if v > 30 else "#2e7d32" for v in pct_low]

    fig = go.Figure(go.Bar(
        x=params, y=pct_low,
        marker_color=colors,
        text=[f"{v:.0f}%" for v in pct_low],
        textposition="outside",
    ))
    fig.update_layout(
        yaxis=dict(range=[0, 115], showgrid=True, gridcolor="#eee", title="% area"),
        xaxis=dict(showgrid=False),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=40, r=10, t=10, b=30),
        showlegend=False,
    )
    return fig


@app.callback(Output("conf-hist", "figure"), Input("param-select", "value"))
def update_conf_hist(param):
    df = load_param_data(param)
    if df is None:
        fig = go.Figure()
        fig.add_annotation(text="No maps yet", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(color="#aaa"))
        fig.update_layout(margin=dict(l=20, r=20, t=10, b=20), paper_bgcolor="white")
        return fig

    fig = go.Figure(go.Histogram(x=df["confidence"], nbinsx=20,
                                  marker_color=GREEN, opacity=0.8))
    fig.add_vline(x=0.75, line_dash="dash", line_color=AMBER,
                  annotation_text="High conf threshold", annotation_font_size=11,
                  annotation_position="top right")
    fig.update_layout(
        xaxis=dict(title="Confidence Score", range=[0, 1]),
        yaxis=dict(title="Pixels"),
        plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=40, r=10, t=10, b=40),
        showlegend=False,
    )
    return fig

# ---------------------------------------------------------------------------
# Callbacks — Farmer Advisory
# ---------------------------------------------------------------------------

@app.callback(Output("lang-store", "data"), Input("lang-toggle", "value"))
def sync_lang_store(val):
    return val


@app.callback(Output("rec-btn", "children"), Input("lang-store", "data"))
def update_btn_label(lang):
    icon = html.I(className="bi bi-calculator me-2")
    if lang == "te":
        return [icon, TELUGU["gen_btn"]]
    return [icon, "Generate Recommendation"]


@app.callback(Output("yield-input", "value"), Input("crop-select", "value"))
def update_default_yield(crop):
    return DEFAULT_TARGET_YIELD.get(crop, 5.0)


@app.callback(
    Output("rec-output", "children"),
    Input("rec-btn", "n_clicks"),
    State("crop-select", "value"),
    State("area-input",  "value"),
    State("yield-input", "value"),
    State("sl-ph",  "value"), State("sl-ec", "value"), State("sl-oc", "value"),
    State("sl-n",   "value"), State("sl-p",  "value"), State("sl-k",  "value"),
    State("inp-zn", "value"), State("inp-fe","value"),
    State("inp-b",  "value"), State("inp-cu","value"),
    State("lang-store", "data"),
    prevent_initial_call=True,
)
def generate_recommendation(_, crop, area, t_yield,
                              ph, ec, oc, n, p, k, zn, fe, b, cu, lang):
    soil = {
        "pH": ph or 7.0, "EC": ec or 0.5, "OC": oc or 0.4,
        "N": n or 200,   "P": p or 20,    "K": k or 150,
        "Zn": zn or 0.0, "Fe": fe or 0.0, "B": b or 0.0, "Cu": cu or 0.0,
    }
    area    = float(area or 1.0)
    t_yield = float(t_yield or DEFAULT_TARGET_YIELD[crop])
    lang    = lang or "en"
    te      = lang == "te"
    rec     = full_recommendation(crop, soil, t_yield, area)

    # ── Dose summary cards (N / P / K) ───────────────────────────────────────
    dose_cards = []
    for nutrient, r in rec["macronutrients"].items():
        dose = r["dose_kg_ha"]
        color = "success" if dose == 0 else "warning" if dose < 60 else "danger"
        unit_lbl = TELUGU["col_kg_ha"] if te else "kg / ha total"
        dose_cards.append(dbc.Col(
            dbc.Card([dbc.CardBody([
                html.P(nutrient, className="text-muted fw-bold mb-0 small"),
                html.H2(f"{dose:.0f}", className="fw-bold mb-0"),
                html.Small(unit_lbl),
            ], className="text-center py-2")], color=color, outline=True, className="shadow-sm"),
            xs=4,
        ))

    # ── NPK split schedule table ──────────────────────────────────────────────
    rows = []
    for nutrient, r in rec["macronutrients"].items():
        for split in r["splits"]:
            rows.append({
                (TELUGU["col_nutrient"] if te else "Nutrient"): nutrient,
                (TELUGU["col_timing"]   if te else "Timing"):   split["timing"],
                (TELUGU["col_kg_ha"]    if te else "kg / ha"):  split["dose_kg_ha"],
                (TELUGU["col_kg_acre"]  if te else "kg / acre"): round(split["dose_kg_ha"] * 0.4047, 1),
            })

    if rows:
        table = dbc.Table.from_dataframe(
            pd.DataFrame(rows),
            striped=True, bordered=False, hover=True,
            responsive=True, className="small mb-0",
        )
    else:
        no_macro_msg = TELUGU["no_macro"] if te else "Soil nutrient levels are adequate — no macronutrient application needed."
        table = dbc.Alert(no_macro_msg, color="success", className="mb-0")

    # ── Micronutrient alerts ──────────────────────────────────────────────────
    micro_items = []
    for m in rec["micronutrients"]:
        if te:
            body = [
                html.I(className="bi bi-exclamation-triangle-fill me-2"),
                html.Strong(f"{m['nutrient']} {TELUGU['deficiency']} — "),
                f"{TELUGU['apply']} {m['carrier']}: {m['dose_kg_ha']} {TELUGU['col_kg_ha']} "
                f"({m['dose_kg_acre']} {TELUGU['col_kg_acre']}). ",
                html.Strong(m["timing"]),
                html.Div(html.Small(m.get("foliar", ""), className="text-muted")) if m.get("foliar") else None,
            ]
        else:
            body = [
                html.I(className="bi bi-exclamation-triangle-fill me-2"),
                html.Strong(f"{m['nutrient']} deficiency — "),
                f"Apply {m['carrier']}: {m['dose_kg_ha']} kg/ha ({m['dose_kg_acre']} kg/acre). ",
                html.Strong(m["timing"]),
                html.Div(html.Small(m.get("foliar", ""), className="text-muted")) if m.get("foliar") else None,
            ]
        micro_items.append(dbc.Alert(body, color="warning", className="mb-2 py-2"))

    if not micro_items:
        no_micro_msg = TELUGU["no_micro"] if te else "No micronutrient deficiencies detected."
        micro_items = [dbc.Alert([html.I(className="bi bi-check-circle me-2"), no_micro_msg],
                                  color="success", className="mb-2")]

    # ── Cost savings ─────────────────────────────────────────────────────────
    savings = rec["estimated_savings_inr"]
    if savings > 0:
        if te:
            savings_el = dbc.Alert([
                html.I(className="bi bi-cash-coin me-2"),
                html.Strong(f"₹{savings:,.0f} "),
                f"{TELUGU['savings_txt']} {area} {TELUGU['acres']}కు",
            ], color="success", className="mb-0")
        else:
            savings_el = dbc.Alert([
                html.I(className="bi bi-cash-coin me-2"),
                html.Strong(f"₹{savings:,.0f} estimated savings "),
                f"vs. blanket application for {area} acres",
            ], color="success", className="mb-0")
    else:
        savings_el = None

    # ── Top confirmation banner ───────────────────────────────────────────────
    crop_name = CROPS_TE.get(crop, crop) if te else CROPS.get(crop, crop)
    if te:
        banner_text = f" | {area} {TELUGU['acres']} | {TELUGU['target']} {t_yield} t/ha"
    else:
        banner_text = f" | {area} acres | Target {t_yield} t/ha"

    npk_header   = TELUGU["npk_schedule"]  if te else "NPK Application Schedule"
    micro_header = TELUGU["micro_correct"] if te else "Micronutrient Corrections"

    return html.Div([
        dbc.Alert([
            html.I(className="bi bi-check-circle-fill me-2"),
            html.Strong(crop_name),
            banner_text,
        ], color="success", className="mb-3"),

        dbc.Row(dose_cards, className="mb-3 g-2"),

        dbc.Card([
            dbc.CardHeader(html.Strong(npk_header)),
            dbc.CardBody(table, className="p-2"),
        ], className="shadow-sm mb-3"),

        dbc.Card([
            dbc.CardHeader(html.Strong(micro_header)),
            dbc.CardBody(micro_items, className="pb-1"),
        ], className="shadow-sm mb-3"),

        savings_el,
    ])


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    host = os.environ.get("DASH_HOST", "127.0.0.1")
    print("Starting Soil Health Intelligence Dashboard...")
    print(f"Open http://localhost:8050 in your browser\n")
    app.run(debug=False, host=host, port=8050)
