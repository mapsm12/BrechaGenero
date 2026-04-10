#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from io import StringIO
from functools import lru_cache
import os
import json
import logging
import traceback
import numpy as np
import pandas as pd

from dash import Dash, html, dcc, Input, Output, State, dash_table, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# LOGGING
# ============================================================
LOG_LEVEL = os.environ.get("APP_LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("hackathon_dashboard")

# ============================================================
# CONFIG
# ============================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data_dashboard"

PARQUET_FILE = DATA_DIR / "base_dashboard_v3.parquet"
CSV_FILE = DATA_DIR / "base_dashboard_v3.csv"

CENT_FILE = DATA_DIR / "peru_departamentos_centroids_v3.csv"
METRIC_CATALOG_FILE = DATA_DIR / "metric_catalog_v3.csv"
META_FILE = DATA_DIR / "dashboard_v3_metadata.json"

JNE_DEP_FILE = DATA_DIR / "metricas_jne_departamento_anio_v3.csv"
JNE_NAT_FILE = DATA_DIR / "metricas_jne_nacional_anio_v3.csv"
JNE_DEP_ALL_FILE = DATA_DIR / "metricas_jne_departamento_consolidado_v3.csv"
JNE_NAT_ALL_FILE = DATA_DIR / "metricas_jne_nacional_consolidado_v3.csv"

PORT = int(os.environ.get("PORT", 8051))

# ============================================================
# ARCHIVOS
# ============================================================
required_files = [
    CENT_FILE,
    METRIC_CATALOG_FILE,
    META_FILE,
    JNE_DEP_FILE,
    JNE_NAT_FILE,
    JNE_DEP_ALL_FILE,
    JNE_NAT_ALL_FILE,
]
for fp in required_files:
    if not fp.exists():
        raise FileNotFoundError(f"No existe el archivo requerido: {fp}")

if PARQUET_FILE.exists():
    logger.info("Leyendo base principal desde parquet: %s", PARQUET_FILE)
    DF = pd.read_parquet(PARQUET_FILE)
elif CSV_FILE.exists():
    logger.info("Leyendo base principal desde CSV: %s", CSV_FILE)
    DF = pd.read_csv(CSV_FILE, encoding="utf-8-sig", low_memory=False)
else:
    raise FileNotFoundError(f"No existe ni {PARQUET_FILE.name} ni {CSV_FILE.name}")

CENT = pd.read_csv(CENT_FILE, encoding="utf-8-sig")
METRIC_CATALOG_DF = pd.read_csv(METRIC_CATALOG_FILE, encoding="utf-8-sig")
JNE_DEP = pd.read_csv(JNE_DEP_FILE, encoding="utf-8-sig")
JNE_NAT = pd.read_csv(JNE_NAT_FILE, encoding="utf-8-sig")
JNE_DEP_ALL = pd.read_csv(JNE_DEP_ALL_FILE, encoding="utf-8-sig")
JNE_NAT_ALL = pd.read_csv(JNE_NAT_ALL_FILE, encoding="utf-8-sig")

with open(META_FILE, "r", encoding="utf-8") as f:
    META = json.load(f)

# ============================================================
# ESTILO
# ============================================================
BG = "#f6eff7"
CARD = "#ffffff"
BORDER = "#ead7ef"
TEXT = "#2f1836"
MUTED = "#6c5b74"
PURPLE = "#8e24aa"
PINK = "#d81b60"
CYAN = "#00acc1"
BLUE = "#1e88e5"
SOFT = "#f8ebf8"
SOFT2 = "#fff7fc"
SUCCESS = "#1b9e77"
WARNING = "#f39c12"
DANGER = "#c2185b"

# ============================================================
# HELPERS DE LOG
# ============================================================
def log_df_info(name, df, max_cols=20):
    if df is None:
        logger.info("[%s] df=None", name)
        return
    logger.info("[%s] shape=%s", name, df.shape)
    cols_preview = list(df.columns[:max_cols])
    logger.info("[%s] columnas preview=%s", name, cols_preview)
    try:
        dtypes_preview = {c: str(df[c].dtype) for c in df.columns[:min(len(df.columns), 10)]}
        logger.info("[%s] dtypes preview=%s", name, dtypes_preview)
    except Exception as e:
        logger.warning("[%s] no se pudo loggear dtypes: %s", name, e)

# ============================================================
# NORMALIZACIÓN
# ============================================================
def normalize_dep_cod_series(s, zfill=2):
    if s is None:
        return s
    return (
        s.astype("string")
         .str.replace(r"\.0$", "", regex=True)
         .str.strip()
         .replace({"<NA>": pd.NA, "nan": pd.NA, "None": pd.NA})
         .str.zfill(zfill)
    )

def normalize_dep_fields(df, dep_col="dep_cod", dep_name_col="departamento", zfill=2):
    out = df.copy()
    if dep_col in out.columns:
        out[dep_col] = normalize_dep_cod_series(out[dep_col], zfill=zfill)
    if dep_name_col in out.columns:
        out[dep_name_col] = out[dep_name_col].astype("string").str.strip()
    return out

def normalize_year_col(df, col="anio"):
    out = df.copy()
    if col in out.columns:
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    return out

def ensure_unique_columns(df, df_name="df"):
    if df.empty:
        return df
    if df.columns.duplicated().any():
        dupes = df.columns[df.columns.duplicated()].tolist()
        logger.warning("[%s] columnas duplicadas detectadas y removidas: %s", df_name, dupes)
        df = df.loc[:, ~df.columns.duplicated()].copy()
    return df

def unique_preserve_order(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out

def safe_get_scalar(v):
    if isinstance(v, pd.DataFrame):
        if v.size == 0:
            return np.nan
        logger.warning("safe_get_scalar recibió DataFrame; usando primer valor.")
        return safe_get_scalar(v.iloc[0, 0])

    if isinstance(v, pd.Series):
        if len(v) == 0:
            return np.nan
        if len(v) > 1:
            logger.warning("safe_get_scalar recibió Series de largo %s; usando primer valor.", len(v))
        return safe_get_scalar(v.iloc[0])

    if isinstance(v, (list, tuple, np.ndarray)):
        if len(v) == 0:
            return np.nan
        return safe_get_scalar(v[0])

    return v

# Normalización inicial
DF = normalize_dep_fields(DF, dep_col="DEP_COD", dep_name_col="DEPARTAMENTO")
CENT = normalize_dep_fields(CENT, dep_col="dep_cod", dep_name_col="departamento")
JNE_DEP = normalize_dep_fields(JNE_DEP, dep_col="dep_cod", dep_name_col="departamento")
JNE_DEP_ALL = normalize_dep_fields(JNE_DEP_ALL, dep_col="dep_cod", dep_name_col="departamento")
JNE_DEP = normalize_year_col(JNE_DEP, "anio")
JNE_NAT = normalize_year_col(JNE_NAT, "anio")

log_df_info("DF_base", DF)
log_df_info("CENT", CENT)
log_df_info("JNE_DEP", JNE_DEP)
log_df_info("JNE_NAT", JNE_NAT)

DEFAULT_YEAR = int(META.get("default_year", int(pd.to_numeric(DF["ANIO_ENCUESTA"], errors="coerce").dropna().max())))
DEFAULT_METRIC = META.get("default_metric", "indice_habilitante_liderazgo_femenino_0_100")
DEFAULT_DEPARTMENT = META.get("default_department", "Lima")

METRIC_OPTIONS = METRIC_CATALOG_DF.to_dict("records")
METRIC_MAP = {r["id"]: r for r in METRIC_OPTIONS}
METRIC_IDS = list(METRIC_MAP.keys())

YEARS = sorted(pd.to_numeric(DF["ANIO_ENCUESTA"], errors="coerce").dropna().astype(int).unique().tolist())
DEPARTMENTS = sorted(DF["DEPARTAMENTO"].dropna().astype(str).unique().tolist()) if "DEPARTAMENTO" in DF.columns else []
CLASS_OPTIONS = sorted(DF["CLASE_SOCIAL_PROXY"].dropna().astype(str).unique().tolist()) if "CLASE_SOCIAL_PROXY" in DF.columns else []
ETH_OPTIONS = sorted(DF["ETNIA_GRUPO"].dropna().astype(str).unique().tolist()) if "ETNIA_GRUPO" in DF.columns else []
OCC_OPTIONS = sorted(DF["OCUPACION_GRUPO"].dropna().astype(str).unique().tolist()) if "OCUPACION_GRUPO" in DF.columns else []
AGE_OPTIONS = sorted(DF["GRUPO_EDAD"].dropna().astype(str).unique().tolist()) if "GRUPO_EDAD" in DF.columns else []
METRIC_GROUPS = sorted(METRIC_CATALOG_DF["group"].dropna().astype(str).unique().tolist())

# ============================================================
# HELPERS GENERALES
# ============================================================
def safe_div(num, den):
    try:
        num = safe_get_scalar(num)
        den = safe_get_scalar(den)
        if den is None or pd.isna(den) or den == 0:
            return np.nan
        return num / den
    except Exception:
        return np.nan

def wmean(x, w):
    x = pd.to_numeric(x, errors="coerce")
    w = pd.to_numeric(w, errors="coerce")
    m = x.notna() & w.notna()
    if m.sum() == 0:
        return np.nan
    return np.average(x[m], weights=w[m])

def wshare(ind, w):
    ind = pd.to_numeric(ind, errors="coerce")
    w = pd.to_numeric(w, errors="coerce")
    m = ind.notna() & w.notna()
    if m.sum() == 0:
        return np.nan
    return np.average(ind[m].astype(float), weights=w[m])

def minmax_series(s):
    s = pd.to_numeric(s, errors="coerce")
    vmin = s.min(skipna=True)
    vmax = s.max(skipna=True)
    if pd.isna(vmin) or pd.isna(vmax):
        return pd.Series(np.nan, index=s.index)
    if vmax == vmin:
        return pd.Series(0.5, index=s.index)
    return (s - vmin) / (vmax - vmin)

def metric_group(metric_id):
    return METRIC_MAP.get(metric_id, {}).get("group", "Otros")

def metric_type(metric_id):
    return METRIC_MAP.get(metric_id, {}).get("type", "level")

def metric_unit(metric_id):
    return METRIC_MAP.get(metric_id, {}).get("unit", "unknown")

def metric_label(metric_id):
    return METRIC_MAP.get(metric_id, {}).get("label", metric_id)

def is_diverging_metric(metric_id, mode="raw"):
    return metric_type(metric_id) in {"gap", "penalty"} or mode == "anom"

def fmt_value(v, metric_id):
    v = safe_get_scalar(v)
    try:
        if pd.isna(v):
            return "NA"
    except Exception:
        return "NA"

    unit = metric_unit(metric_id)
    if unit == "percent":
        return f"{100 * v:,.1f}%"
    if unit == "hours":
        return f"{v:,.2f} h"
    if unit == "income":
        return f"S/ {v:,.2f}"
    if unit == "ratio":
        return f"{v:,.2f}"
    if unit == "count":
        return f"{v:,.2f}"
    if unit == "index":
        return f"{v:,.1f}"
    return f"{v:,.2f}"

def fmt_simple(v):
    v = safe_get_scalar(v)
    if pd.isna(v):
        return "NA"
    return f"{v:,.2f}"

def read_json_df(s):
    if s is None or s == "" or s == "[]":
        return pd.DataFrame()
    return pd.read_json(StringIO(s), orient="records")

def df_to_json(df):
    if df is None or len(df) == 0:
        return "[]"
    return df.to_json(orient="records", date_format="iso")

def make_info_figure(title, message):
    fig = go.Figure()
    fig.add_annotation(
        x=0.5, y=0.5,
        xref="paper", yref="paper",
        text=message,
        showarrow=False,
        font=dict(size=15, color=MUTED),
        align="center",
        bgcolor="rgba(255,255,255,0.0)"
    )
    fig.update_layout(
        title=title,
        template="plotly_white",
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font={"family": "Arial", "color": TEXT},
        margin=dict(l=20, r=20, t=55, b=20),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig

def figure_layout(fig, title=""):
    fig.update_layout(
        title=title,
        template="plotly_white",
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font={"family": "Arial", "color": TEXT},
        margin=dict(l=25, r=20, t=60, b=30),
        title_font={"size": 16, "color": TEXT},
        legend_title_text="",
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Arial"),
    )
    return fig

def card_style():
    return {
        "borderRadius": "20px",
        "border": f"1px solid {BORDER}",
        "boxShadow": "0 8px 20px rgba(142,36,170,0.08)",
        "background": CARD,
    }

def make_kpi_card(title, value, subtitle="", icon="bi bi-bar-chart"):
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.Div(
                            html.I(className=icon, style={"fontSize": "1.1rem", "color": PURPLE}),
                            style={
                                "width": "38px",
                                "height": "38px",
                                "borderRadius": "12px",
                                "display": "flex",
                                "alignItems": "center",
                                "justifyContent": "center",
                                "background": SOFT,
                                "marginBottom": "10px",
                            },
                        ),
                        html.Div(title, style={"fontSize": "0.86rem", "color": MUTED, "fontWeight": "600"}),
                        html.Div(value, style={"fontSize": "1.75rem", "fontWeight": "800", "color": TEXT, "lineHeight": "1.1", "marginTop": "4px"}),
                        html.Div(subtitle, style={"fontSize": "0.8rem", "color": MUTED, "marginTop": "6px"}),
                    ]
                )
            ]
        ),
        style=card_style(),
    )

def color_scale(value, vmin, vmax, metric_id, mode="raw"):
    value = safe_get_scalar(value)
    if pd.isna(value):
        return "#c7c7c7"

    if is_diverging_metric(metric_id, mode=mode):
        vmax_abs = max(abs(vmin), abs(vmax), 1e-9)
        x = max(-1, min(1, value / vmax_abs))
        if x < 0:
            t = abs(x)
            r = int(235 * (1 - t) + 0 * t)
            g = int(243 * (1 - t) + 172 * t)
            b = int(250 * (1 - t) + 193 * t)
        else:
            t = x
            r = int(240 * (1 - t) + 216 * t)
            g = int(233 * (1 - t) + 27 * t)
            b = int(245 * (1 - t) + 96 * t)
        return f"rgb({r},{g},{b})"

    span = max(vmax - vmin, 1e-9)
    t = (value - vmin) / span
    t = max(0, min(1, t))
    r = int(250 * (1 - t) + 142 * t)
    g = int(235 * (1 - t) + 36 * t)
    b = int(246 * (1 - t) + 170 * t)
    return f"rgb({r},{g},{b})"

def pick_sample_column(metric_id):
    grp = metric_group(metric_id)
    if grp in {"Maternidad proxy", "Cruce cuidado-educación"}:
        return "n_mujeres_18_49"
    if grp in {"Representación política", "Liderazgo político"}:
        return "total_autoridades_electas"
    return "n_adultos_18_64"

def table_format_series(s, metric_id):
    if isinstance(s, pd.DataFrame):
        logger.warning("table_format_series recibió DataFrame para metric_id=%s; usando primera columna.", metric_id)
        s = s.iloc[:, 0]
    return s.map(lambda x: fmt_value(x, metric_id))

def filter_metric_options_by_group(group_value):
    rows = METRIC_OPTIONS
    if group_value and group_value != "Todas":
        rows = [r for r in rows if str(r.get("group", "")) == str(group_value)]
    return rows

# ============================================================
# EXPLICACIÓN DINÁMICA DE MÉTRICAS
# ============================================================
def metric_semantics(metric_id):
    t = metric_type(metric_id)
    u = metric_unit(metric_id)

    # Casos específicos
    if metric_id in {"gap_trabaja_horas_h_m", "gap_horas_h_m", "gap_ingreso_hogar_h_m"}:
        return {
            "definition": "Diferencia entre hombres y mujeres.",
            "reading": "Cercano a 0 indica paridad. Positivo favorece a hombres. Negativo favorece a mujeres.",
            "range_hint": "El signo es más importante que el tamaño absoluto."
        }

    if metric_id in {"gap_pobreza_m_h"}:
        return {
            "definition": "Diferencia de pobreza entre mujeres y hombres.",
            "reading": "Cercano a 0 indica incidencias similares. Positivo significa mayor pobreza en mujeres. Negativo significa mayor pobreza en hombres.",
            "range_hint": "Mientras más positivo, mayor desventaja femenina en pobreza."
        }

    if metric_id in {"gap_educ_sup_m_h", "gap_educ_univ_m_h"}:
        return {
            "definition": "Diferencia en acceso educativo entre mujeres y hombres.",
            "reading": "Cercano a 0 indica paridad. Positivo indica mayor presencia femenina. Negativo indica mayor presencia masculina.",
            "range_hint": "El signo y la distancia respecto de 0 son clave."
        }

    if metric_id in {"ratio_trabajo_m_h", "ratio_horas_m_h", "ratio_ingreso_hogar_m_h", "ratio_educ_sup_m_h", "ratio_autoridades_mujer_hombre"}:
        return {
            "definition": "Razón mujer / hombre.",
            "reading": "Cercano a 1 indica paridad. Menor que 1 sugiere desventaja femenina. Mayor que 1 sugiere ventaja o sobrerrepresentación femenina.",
            "range_hint": "1 es el punto de referencia."
        }

    if metric_id in {"ratio_pobreza_m_h"}:
        return {
            "definition": "Razón de pobreza de mujeres respecto a hombres.",
            "reading": "Cercano a 1 indica niveles similares. Mayor que 1 indica que la pobreza femenina es más alta. Menor que 1 indica mayor pobreza masculina.",
            "range_hint": "1 es el punto de referencia."
        }

    if metric_id == "indice_techo_politico_mujeres":
        return {
            "definition": "Compara la presencia femenina en cargos de liderazgo respecto a su presencia total entre autoridades.",
            "reading": "Cercano a 1 indica representación proporcional. Menor que 1 sugiere techo político. Mayor que 1 sugiere sobrepresencia femenina en liderazgo.",
            "range_hint": "1 es el valor clave."
        }

    if metric_id == "brecha_liderazgo_vs_base_mujeres":
        return {
            "definition": "Diferencia entre la presencia femenina en liderazgo y la presencia femenina total en autoridades.",
            "reading": "Cercano a 0 indica proporcionalidad. Negativo sugiere techo político. Positivo sugiere mayor presencia femenina en liderazgo que en el total.",
            "range_hint": "0 es el punto de referencia."
        }

    if metric_id in {"penalidad_maternidad_trabajo", "penalidad_maternidad_horas", "penalidad_maternidad_ingreso"}:
        return {
            "definition": "Diferencia entre mujeres con niño/a menor de 6 años en el hogar y mujeres sin esa condición.",
            "reading": "Cercano a 0 indica poca o nula penalidad. Negativo indica penalidad para mujeres con U6. Positivo indica ventaja del grupo con U6.",
            "range_hint": "0 es el punto de referencia."
        }

    if metric_id in {"penalidad_maternidad_pobreza"}:
        return {
            "definition": "Diferencia en pobreza entre mujeres con U6 y sin U6.",
            "reading": "Cercano a 0 indica poca diferencia. Positivo indica mayor pobreza entre mujeres con U6. Negativo indica menor pobreza en ese grupo.",
            "range_hint": "0 es el punto de referencia."
        }

    if metric_id in {"share_autoridades_mujeres", "share_liderazgo_ejecutivo_mujeres", "share_alcaldias_mujeres", "share_gobernaciones_mujeres", "share_regidurias_mujeres", "share_consejerias_mujeres"}:
        return {
            "definition": "Proporción de mujeres dentro del universo político considerado.",
            "reading": "Cercano a 0 indica presencia muy baja. Cercano a 0.5 indica paridad. Cercano a 1 indica presencia femenina muy alta.",
            "range_hint": "0.5 es una referencia útil de paridad."
        }

    if metric_id == "share_mujeres_18_49_con_u6":
        return {
            "definition": "Proporción de mujeres de 18–49 años que viven en hogares con niño/a menor de 6 años.",
            "reading": "Cercano a 0 indica baja exposición al proxy de cuidado intensivo. Valores más altos indican mayor presencia del grupo potencialmente afectado por cuidados.",
            "range_hint": "Es una métrica de exposición, no de ventaja o desventaja directa."
        }

    if u == "index":
        return {
            "definition": "Índice sintético construido con varias dimensiones.",
            "reading": "Cercano a 0 indica un entorno poco favorable. Cercano a 100 indica un entorno más habilitante.",
            "range_hint": "Se interpreta de forma relativa entre departamentos y años."
        }

    if u == "percent":
        if "pobreza" in metric_id:
            return {
                "definition": "Proporción o tasa porcentual.",
                "reading": "Cercano a 0 indica incidencia baja. Valores más altos indican peor situación en pobreza.",
                "range_hint": "Se interpreta en porcentaje."
            }
        return {
            "definition": "Proporción o tasa porcentual.",
            "reading": "Cercano a 0 indica presencia baja. Cercano a 1 indica presencia muy alta.",
            "range_hint": "En indicadores de participación, valores más altos suelen indicar mayor presencia."
        }

    if u == "ratio":
        return {
            "definition": "Razón entre dos grupos.",
            "reading": "Cercano a 1 indica similitud relativa. Valores por debajo o por encima muestran asimetrías.",
            "range_hint": "1 es el punto de referencia."
        }

    if u == "income":
        return {
            "definition": "Valor monetario promedio.",
            "reading": "Valores más altos indican mayores ingresos promedio. En brechas y penalidades, el signo es clave.",
            "range_hint": "Mira tanto el nivel como la comparación con Perú."
        }

    if u == "hours":
        return {
            "definition": "Promedio de horas.",
            "reading": "Valores más altos indican mayor intensidad horaria. En brechas y penalidades, el signo es clave.",
            "range_hint": "Mira tanto el nivel como la comparación con Perú."
        }

    return {
        "definition": "Indicador cuantitativo.",
        "reading": "Interprétalo comparando el valor del departamento, Perú y la posición en el ranking.",
        "range_hint": "La referencia puede ser 0, 1 o el promedio nacional según el tipo de métrica."
    }

def build_metric_interpretation_card(metric_id, focus_val, nat_val, anom_val, dep_name):
    sem = metric_semantics(metric_id)
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        html.Div("¿Cómo leer esta métrica?", style={"fontWeight": "800", "fontSize": "1.05rem", "color": TEXT}),
                        html.Div(metric_label(metric_id), style={"color": PURPLE, "fontWeight": "700", "marginTop": "2px"}),
                    ],
                    style={"marginBottom": "10px"},
                ),
                html.Div(
                    [
                        html.Div("Definición", style={"fontWeight": "700", "color": TEXT}),
                        html.Div(sem["definition"], style={"color": MUTED, "marginBottom": "8px"}),
                        html.Div("Lectura", style={"fontWeight": "700", "color": TEXT}),
                        html.Div(sem["reading"], style={"color": MUTED, "marginBottom": "8px"}),
                        html.Div("Referencia", style={"fontWeight": "700", "color": TEXT}),
                        html.Div(sem["range_hint"], style={"color": MUTED, "marginBottom": "10px"}),
                    ]
                ),
                html.Hr(),
                html.Div(
                    [
                        html.Div("Lectura puntual del departamento", style={"fontWeight": "700", "color": TEXT, "marginBottom": "6px"}),
                        html.Div(
                            f"{dep_name}: {fmt_value(focus_val, metric_id)} · Perú: {fmt_value(nat_val, metric_id)} · Anomalía: {fmt_value(anom_val, metric_id)}",
                            style={"color": TEXT}
                        ),
                    ]
                ),
            ]
        ),
        style=card_style(),
    )

def build_general_reading(metric_id, dep_name, dep_value, nat_value, anom_value, best_dep, best_value, rank_text):
    sem = metric_semantics(metric_id)
    txt = (
        f"En {dep_name}, {metric_label(metric_id).lower()} alcanza {fmt_value(dep_value, metric_id)}. "
        f"El valor nacional es {fmt_value(nat_value, metric_id)} y la diferencia respecto a Perú es {fmt_value(anom_value, metric_id)}. "
        f"En el ranking territorial, {dep_name} se ubica en {rank_text}. "
        f"El valor más alto observado corresponde a {best_dep} con {fmt_value(best_value, metric_id)}. "
        f"Interpretativamente: {sem['reading']}"
    )
    return dbc.Alert(
        [
            html.Div(html.B("Lectura general automática"), className="mb-1"),
            html.Div(txt),
        ],
        color="light",
        style={"borderRadius": "16px", "border": f"1px solid {BORDER}", "background": SOFT2},
    )

# ============================================================
# FILTROS ENAHO
# ============================================================
def apply_filters_enaho(df, clase="Todas", etnia="Todas", ocupacion="Todas", grupo_edad="Todas"):
    out = df.copy()

    if clase != "Todas" and "CLASE_SOCIAL_PROXY" in out.columns:
        out = out[out["CLASE_SOCIAL_PROXY"].astype(str) == str(clase)]

    if etnia != "Todas" and "ETNIA_GRUPO" in out.columns:
        out = out[out["ETNIA_GRUPO"].astype(str) == str(etnia)]

    if ocupacion != "Todas" and "OCUPACION_GRUPO" in out.columns:
        out = out[out["OCUPACION_GRUPO"].astype(str) == str(ocupacion)]

    if grupo_edad != "Todas" and "GRUPO_EDAD" in out.columns:
        out = out[out["GRUPO_EDAD"].astype(str) == str(grupo_edad)]

    return out

# ============================================================
# MÉTRICAS ENAHO DINÁMICAS
# ============================================================
def build_metric_row_enaho(g):
    out = {}

    ga = g[
        g["SEXO"].isin([1, 2]) &
        g["EDAD"].between(18, 64, inclusive="both")
    ].copy()

    gh = ga[ga["SEXO"] == 1].copy()
    gm = ga[ga["SEXO"] == 2].copy()

    gh_work = gh[gh["TRABAJA_HORAS"] == 1].copy()
    gm_work = gm[gm["TRABAJA_HORAS"] == 1].copy()

    out["n_adultos_18_64"] = len(ga)
    out["peso_total_18_64"] = ga["PESO"].sum()

    out["tasa_trabaja_horas_hombre"] = wshare(gh["TRABAJA_HORAS"], gh["PESO"])
    out["tasa_trabaja_horas_mujer"] = wshare(gm["TRABAJA_HORAS"], gm["PESO"])

    out["horas_prom_hombre"] = wmean(gh_work["HORAS_TRABAJADAS_TOTAL"], gh_work["PESO"])
    out["horas_prom_mujer"] = wmean(gm_work["HORAS_TRABAJADAS_TOTAL"], gm_work["PESO"])

    out["pobreza_hombre"] = wshare(gh["POBRE_BIN"], gh["PESO"])
    out["pobreza_mujer"] = wshare(gm["POBRE_BIN"], gm["PESO"])

    out["ingreso_neto_hogar_hombre"] = wmean(gh["INGRESO_NETO_HOGAR"], gh["PESO"])
    out["ingreso_neto_hogar_mujer"] = wmean(gm["INGRESO_NETO_HOGAR"], gm["PESO"])

    if "ES_EDUC_SUPERIOR" in g.columns:
        out["tasa_educ_sup_hombre"] = wshare(gh["ES_EDUC_SUPERIOR"], gh["PESO"])
        out["tasa_educ_sup_mujer"] = wshare(gm["ES_EDUC_SUPERIOR"], gm["PESO"])
    else:
        out["tasa_educ_sup_hombre"] = np.nan
        out["tasa_educ_sup_mujer"] = np.nan

    if "ES_EDUC_UNIVERSITARIA" in g.columns:
        out["tasa_educ_univ_hombre"] = wshare(gh["ES_EDUC_UNIVERSITARIA"], gh["PESO"])
        out["tasa_educ_univ_mujer"] = wshare(gm["ES_EDUC_UNIVERSITARIA"], gm["PESO"])
    else:
        out["tasa_educ_univ_hombre"] = np.nan
        out["tasa_educ_univ_mujer"] = np.nan

    out["gap_trabaja_horas_h_m"] = out["tasa_trabaja_horas_hombre"] - out["tasa_trabaja_horas_mujer"]
    out["gap_horas_h_m"] = out["horas_prom_hombre"] - out["horas_prom_mujer"]
    out["gap_pobreza_m_h"] = out["pobreza_mujer"] - out["pobreza_hombre"]
    out["gap_ingreso_hogar_h_m"] = out["ingreso_neto_hogar_hombre"] - out["ingreso_neto_hogar_mujer"]

    out["gap_educ_sup_m_h"] = out["tasa_educ_sup_mujer"] - out["tasa_educ_sup_hombre"]
    out["ratio_educ_sup_m_h"] = safe_div(out["tasa_educ_sup_mujer"], out["tasa_educ_sup_hombre"])
    out["gap_educ_univ_m_h"] = out["tasa_educ_univ_mujer"] - out["tasa_educ_univ_hombre"]

    out["ratio_trabajo_m_h"] = safe_div(out["tasa_trabaja_horas_mujer"], out["tasa_trabaja_horas_hombre"])
    out["ratio_horas_m_h"] = safe_div(out["horas_prom_mujer"], out["horas_prom_hombre"])
    out["ratio_ingreso_hogar_m_h"] = safe_div(out["ingreso_neto_hogar_mujer"], out["ingreso_neto_hogar_hombre"])
    out["ratio_pobreza_m_h"] = safe_div(out["pobreza_mujer"], out["pobreza_hombre"])

    mm = g[
        (g["SEXO"] == 2) &
        (g["EDAD"].between(18, 49, inclusive="both"))
    ].copy()

    mm_no = mm[mm["TIENE_NINIO_U6_HOGAR"] == 0].copy()
    mm_si = mm[mm["TIENE_NINIO_U6_HOGAR"] == 1].copy()

    mm_no_work = mm_no[mm_no["TRABAJA_HORAS"] == 1].copy()
    mm_si_work = mm_si[mm_si["TRABAJA_HORAS"] == 1].copy()

    out["n_mujeres_18_49"] = len(mm)
    out["peso_mujeres_18_49"] = mm["PESO"].sum()

    out["share_mujeres_18_49_con_u6"] = wshare(mm["TIENE_NINIO_U6_HOGAR"], mm["PESO"])

    if "N_NINIOS_U6_HOGAR" in mm.columns:
        out["prom_ninios_u6_hogar_mujer_18_49"] = wmean(mm["N_NINIOS_U6_HOGAR"], mm["PESO"])
        out["share_mujeres_18_49_con_2mas_u6"] = wshare((pd.to_numeric(mm["N_NINIOS_U6_HOGAR"], errors="coerce") >= 2).astype(float), mm["PESO"])
    else:
        out["prom_ninios_u6_hogar_mujer_18_49"] = np.nan
        out["share_mujeres_18_49_con_2mas_u6"] = np.nan

    out["tasa_trabaja_mujer_no_u6"] = wshare(mm_no["TRABAJA_HORAS"], mm_no["PESO"])
    out["tasa_trabaja_mujer_si_u6"] = wshare(mm_si["TRABAJA_HORAS"], mm_si["PESO"])

    out["horas_mujer_no_u6"] = wmean(mm_no_work["HORAS_TRABAJADAS_TOTAL"], mm_no_work["PESO"])
    out["horas_mujer_si_u6"] = wmean(mm_si_work["HORAS_TRABAJADAS_TOTAL"], mm_si_work["PESO"])

    out["pobreza_mujer_no_u6"] = wshare(mm_no["POBRE_BIN"], mm_no["PESO"])
    out["pobreza_mujer_si_u6"] = wshare(mm_si["POBRE_BIN"], mm_si["PESO"])

    out["ingreso_hogar_mujer_no_u6"] = wmean(mm_no["INGRESO_NETO_HOGAR"], mm_no["PESO"])
    out["ingreso_hogar_mujer_si_u6"] = wmean(mm_si["INGRESO_NETO_HOGAR"], mm_si["PESO"])

    out["penalidad_maternidad_trabajo"] = out["tasa_trabaja_mujer_si_u6"] - out["tasa_trabaja_mujer_no_u6"]
    out["penalidad_maternidad_horas"] = out["horas_mujer_si_u6"] - out["horas_mujer_no_u6"]
    out["penalidad_maternidad_pobreza"] = out["pobreza_mujer_si_u6"] - out["pobreza_mujer_no_u6"]
    out["penalidad_maternidad_ingreso"] = out["ingreso_hogar_mujer_si_u6"] - out["ingreso_hogar_mujer_no_u6"]

    if "ES_EDUC_SUPERIOR" in mm.columns:
        mm_sup = mm[mm["ES_EDUC_SUPERIOR"] == 1].copy()
        mm_nosup = mm[mm["ES_EDUC_SUPERIOR"] == 0].copy()

        mm_sup_no = mm_sup[mm_sup["TIENE_NINIO_U6_HOGAR"] == 0].copy()
        mm_sup_si = mm_sup[mm_sup["TIENE_NINIO_U6_HOGAR"] == 1].copy()
        mm_nosup_no = mm_nosup[mm_nosup["TIENE_NINIO_U6_HOGAR"] == 0].copy()
        mm_nosup_si = mm_nosup[mm_nosup["TIENE_NINIO_U6_HOGAR"] == 1].copy()

        out["penalidad_maternidad_trabajo_educ_sup"] = (
            wshare(mm_sup_si["TRABAJA_HORAS"], mm_sup_si["PESO"]) -
            wshare(mm_sup_no["TRABAJA_HORAS"], mm_sup_no["PESO"])
        )
        out["penalidad_maternidad_trabajo_no_educ_sup"] = (
            wshare(mm_nosup_si["TRABAJA_HORAS"], mm_nosup_si["PESO"]) -
            wshare(mm_nosup_no["TRABAJA_HORAS"], mm_nosup_no["PESO"])
        )
        out["mitigacion_penalidad_trabajo_por_educ"] = (
            out["penalidad_maternidad_trabajo_educ_sup"] -
            out["penalidad_maternidad_trabajo_no_educ_sup"]
        )

        out["penalidad_maternidad_ingreso_educ_sup"] = (
            wmean(mm_sup_si["INGRESO_NETO_HOGAR"], mm_sup_si["PESO"]) -
            wmean(mm_sup_no["INGRESO_NETO_HOGAR"], mm_sup_no["PESO"])
        )
        out["penalidad_maternidad_ingreso_no_educ_sup"] = (
            wmean(mm_nosup_si["INGRESO_NETO_HOGAR"], mm_nosup_si["PESO"]) -
            wmean(mm_nosup_no["INGRESO_NETO_HOGAR"], mm_nosup_no["PESO"])
        )
        out["mitigacion_penalidad_ingreso_por_educ"] = (
            out["penalidad_maternidad_ingreso_educ_sup"] -
            out["penalidad_maternidad_ingreso_no_educ_sup"]
        )
    else:
        out["penalidad_maternidad_trabajo_educ_sup"] = np.nan
        out["penalidad_maternidad_trabajo_no_educ_sup"] = np.nan
        out["mitigacion_penalidad_trabajo_por_educ"] = np.nan
        out["penalidad_maternidad_ingreso_educ_sup"] = np.nan
        out["penalidad_maternidad_ingreso_no_educ_sup"] = np.nan
        out["mitigacion_penalidad_ingreso_por_educ"] = np.nan

    return out

def add_anomalies_vs_national(dep_df, nat_df, metric_ids):
    if dep_df.empty or nat_df.empty:
        return dep_df.copy()

    nat_cols = ["anio"] + [m for m in metric_ids if m in nat_df.columns]
    nat_ren = nat_df[nat_cols].rename(columns={m: f"{m}_nat" for m in nat_cols if m != "anio"})
    out = dep_df.merge(nat_ren, on="anio", how="left")

    for m in metric_ids:
        nat_col = f"{m}_nat"
        if m in out.columns and nat_col in out.columns:
            out[f"{m}_anom_nat"] = out[m] - out[nat_col]
    return out

def build_year_department_tables_enaho(df_filtered):
    rows_dep = []
    rows_nat = []

    geo = df_filtered[df_filtered["DEPARTAMENTO"].notna()].copy()

    for (anio, dep_cod, dep), g in geo.groupby(["ANIO_ENCUESTA", "DEP_COD", "DEPARTAMENTO"], dropna=False, observed=False):
        row = {"anio": int(anio), "dep_cod": dep_cod, "departamento": dep}
        row.update(build_metric_row_enaho(g))
        rows_dep.append(row)

    for anio, g in df_filtered.groupby("ANIO_ENCUESTA", dropna=False, observed=False):
        row = {"anio": int(anio), "departamento": "Perú"}
        row.update(build_metric_row_enaho(g))
        rows_nat.append(row)

    dep_df = pd.DataFrame(rows_dep)
    nat_df = pd.DataFrame(rows_nat)

    if not dep_df.empty:
        dep_df = normalize_dep_fields(dep_df, dep_col="dep_cod", dep_name_col="departamento")
        dep_df = normalize_year_col(dep_df, "anio")

        dep_df = dep_df.merge(
            CENT[["dep_cod", "departamento", "lat", "lon"]],
            on=["dep_cod", "departamento"],
            how="left"
        )
        dep_df = ensure_unique_columns(dep_df, "dep_df_post_cent")

        metric_ids = [m for m in METRIC_IDS if m in dep_df.columns and m in nat_df.columns]
        dep_df = add_anomalies_vs_national(dep_df, nat_df, metric_ids)
        dep_df = ensure_unique_columns(dep_df, "dep_df_post_anom")

    nat_df = normalize_year_col(nat_df, "anio")
    nat_df = ensure_unique_columns(nat_df, "nat_df")
    nat_df = nat_df.sort_values("anio").reset_index(drop=True) if not nat_df.empty else nat_df
    dep_df = dep_df.sort_values(["anio", "departamento"]).reset_index(drop=True) if not dep_df.empty else dep_df

    return dep_df, nat_df

def build_consolidated_tables_enaho(df_filtered):
    rows_dep = []
    geo = df_filtered[df_filtered["DEPARTAMENTO"].notna()].copy()

    for (dep_cod, dep), g in geo.groupby(["DEP_COD", "DEPARTAMENTO"], dropna=False, observed=False):
        row = {"periodo": "2008-2024", "dep_cod": dep_cod, "departamento": dep}
        row.update(build_metric_row_enaho(g))
        rows_dep.append(row)

    dep_df = pd.DataFrame(rows_dep)
    if not dep_df.empty:
        dep_df = normalize_dep_fields(dep_df, dep_col="dep_cod", dep_name_col="departamento")
        dep_df = dep_df.merge(
            CENT[["dep_cod", "departamento", "lat", "lon"]],
            on=["dep_cod", "departamento"],
            how="left"
        )
        dep_df = ensure_unique_columns(dep_df, "dep_df_all")

    nat_row = {"periodo": "2008-2024", "departamento": "Perú"}
    nat_row.update(build_metric_row_enaho(df_filtered))
    nat_df = pd.DataFrame([nat_row])

    return dep_df, nat_df

# ============================================================
# INTEGRACIÓN CON JNE + ÍNDICE
# ============================================================
def add_index_by_year(df_in):
    if df_in.empty:
        return df_in.copy()

    df = df_in.copy()
    rows = []

    positive_components = [
        "tasa_educ_sup_mujer",
        "ratio_trabajo_m_h",
        "ratio_ingreso_hogar_m_h",
        "share_autoridades_mujeres",
        "share_liderazgo_ejecutivo_mujeres",
        "penalidad_maternidad_trabajo",
    ]
    negative_components = [
        "pobreza_mujer",
    ]

    for anio, g in df.groupby("anio", dropna=False, observed=False):
        g2 = g.copy()
        score_cols = []

        for col in positive_components:
            if col in g2.columns:
                name = f"_score_{col}"
                g2[name] = minmax_series(g2[col])
                score_cols.append(name)

        for col in negative_components:
            if col in g2.columns:
                name = f"_score_{col}"
                g2[name] = 1 - minmax_series(g2[col])
                score_cols.append(name)

        if len(score_cols) > 0:
            g2["indice_habilitante_liderazgo_femenino_0_100"] = g2[score_cols].mean(axis=1, skipna=True) * 100
            g2["n_componentes_indice_habilitante"] = g2[score_cols].notna().sum(axis=1)
        else:
            g2["indice_habilitante_liderazgo_femenino_0_100"] = np.nan
            g2["n_componentes_indice_habilitante"] = 0

        rows.append(g2)

    out = pd.concat(rows, ignore_index=True) if rows else df.copy()
    out = ensure_unique_columns(out, "add_index_by_year")
    return out

def add_index_single_period(df_in):
    if df_in.empty:
        return df_in.copy()

    df = df_in.copy()

    positive_components = [
        "tasa_educ_sup_mujer",
        "ratio_trabajo_m_h",
        "ratio_ingreso_hogar_m_h",
        "share_autoridades_mujeres",
        "share_liderazgo_ejecutivo_mujeres",
        "penalidad_maternidad_trabajo",
    ]
    negative_components = [
        "pobreza_mujer",
    ]

    score_cols = []

    for col in positive_components:
        if col in df.columns:
            name = f"_score_{col}"
            df[name] = minmax_series(df[col])
            score_cols.append(name)

    for col in negative_components:
        if col in df.columns:
            name = f"_score_{col}"
            df[name] = 1 - minmax_series(df[col])
            score_cols.append(name)

    if len(score_cols) > 0:
        df["indice_habilitante_liderazgo_femenino_0_100"] = df[score_cols].mean(axis=1, skipna=True) * 100
        df["n_componentes_indice_habilitante"] = df[score_cols].notna().sum(axis=1)
    else:
        df["indice_habilitante_liderazgo_femenino_0_100"] = np.nan
        df["n_componentes_indice_habilitante"] = 0

    df = ensure_unique_columns(df, "add_index_single_period")
    return df

def add_index_national_time(df_in):
    if df_in.empty:
        return df_in.copy()

    df = df_in.copy()

    positive_components = [
        "tasa_educ_sup_mujer",
        "ratio_trabajo_m_h",
        "ratio_ingreso_hogar_m_h",
        "share_autoridades_mujeres",
        "share_liderazgo_ejecutivo_mujeres",
        "penalidad_maternidad_trabajo",
    ]
    negative_components = [
        "pobreza_mujer",
    ]

    score_cols = []

    for col in positive_components:
        if col in df.columns:
            name = f"_score_{col}"
            df[name] = minmax_series(df[col])
            score_cols.append(name)

    for col in negative_components:
        if col in df.columns:
            name = f"_score_{col}"
            df[name] = 1 - minmax_series(df[col])
            score_cols.append(name)

    if len(score_cols) > 0:
        df["indice_habilitante_liderazgo_femenino_0_100"] = df[score_cols].mean(axis=1, skipna=True) * 100
        df["n_componentes_indice_habilitante"] = df[score_cols].notna().sum(axis=1)
    else:
        df["indice_habilitante_liderazgo_femenino_0_100"] = np.nan
        df["n_componentes_indice_habilitante"] = 0

    df = ensure_unique_columns(df, "add_index_national_time")
    return df

def merge_with_jne(dep_enaho, nat_enaho):
    dep_enaho = normalize_dep_fields(dep_enaho, dep_col="dep_cod", dep_name_col="departamento")
    dep_enaho = normalize_year_col(dep_enaho, "anio")

    dep = dep_enaho.merge(
        JNE_DEP.drop(columns=["lat", "lon"], errors="ignore"),
        on=["anio", "dep_cod", "departamento"],
        how="left",
        suffixes=("", "_jne")
    )
    dep = ensure_unique_columns(dep, "merge_with_jne_dep")

    nat = nat_enaho.merge(
        JNE_NAT,
        on=["anio", "departamento"],
        how="left",
        suffixes=("", "_jne")
    )
    nat = ensure_unique_columns(nat, "merge_with_jne_nat")

    dep = add_index_by_year(dep)
    nat = add_index_national_time(nat)

    metric_ids_now = [m for m in METRIC_IDS if m in dep.columns and m in nat.columns]
    dep = add_anomalies_vs_national(dep, nat, metric_ids_now)
    dep = ensure_unique_columns(dep, "merge_with_jne_dep_post_anom")

    return dep, nat

def merge_with_jne_all(dep_enaho_all, nat_enaho_all):
    dep_enaho_all = normalize_dep_fields(dep_enaho_all, dep_col="dep_cod", dep_name_col="departamento")

    dep = dep_enaho_all.merge(
        JNE_DEP_ALL.drop(columns=["lat", "lon"], errors="ignore"),
        on=["periodo", "dep_cod", "departamento"],
        how="left",
        suffixes=("", "_jne")
    )
    dep = ensure_unique_columns(dep, "merge_with_jne_all_dep")

    nat = nat_enaho_all.merge(
        JNE_NAT_ALL,
        on=["periodo", "departamento"],
        how="left",
        suffixes=("", "_jne")
    )
    nat = ensure_unique_columns(nat, "merge_with_jne_all_nat")

    dep = add_index_single_period(dep)
    return dep, nat

# ============================================================
# CACHÉ
# ============================================================
@lru_cache(maxsize=64)
def cached_compute_tables(clase, etnia, ocupacion, grupo_edad):
    logger.info(
        "cached_compute_tables | clase=%s | etnia=%s | ocupacion=%s | grupo_edad=%s",
        clase, etnia, ocupacion, grupo_edad
    )

    df_filtered = apply_filters_enaho(
        DF,
        clase=clase,
        etnia=etnia,
        ocupacion=ocupacion,
        grupo_edad=grupo_edad,
    )
    log_df_info("df_filtered", df_filtered)

    dep_enaho, nat_enaho = build_year_department_tables_enaho(df_filtered)
    dep_all_enaho, nat_all_enaho = build_consolidated_tables_enaho(df_filtered)

    dep_integrated, nat_integrated = merge_with_jne(dep_enaho, nat_enaho)
    dep_integrated_all, nat_integrated_all = merge_with_jne_all(dep_all_enaho, nat_all_enaho)

    dep_integrated = normalize_dep_fields(dep_integrated, dep_col="dep_cod", dep_name_col="departamento")
    dep_integrated_all = normalize_dep_fields(dep_integrated_all, dep_col="dep_cod", dep_name_col="departamento")

    dep_integrated = ensure_unique_columns(dep_integrated, "cached_dep_integrated")
    nat_integrated = ensure_unique_columns(nat_integrated, "cached_nat_integrated")
    dep_integrated_all = ensure_unique_columns(dep_integrated_all, "cached_dep_integrated_all")
    nat_integrated_all = ensure_unique_columns(nat_integrated_all, "cached_nat_integrated_all")

    return {
        "dep_integrated": df_to_json(dep_integrated),
        "nat_integrated": df_to_json(nat_integrated),
        "dep_integrated_all": df_to_json(dep_integrated_all),
        "nat_integrated_all": df_to_json(nat_integrated_all),
    }

def build_group_table(df_filtered, by_col):
    rows = []
    if by_col not in df_filtered.columns:
        return pd.DataFrame()

    for group_value, g in df_filtered.groupby(by_col, dropna=False, observed=False):
        row = {by_col: str(group_value)}
        row.update(build_metric_row_enaho(g))
        rows.append(row)

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = ensure_unique_columns(out, f"group_table_{by_col}")
    return out.sort_values(by_col).reset_index(drop=True)

# ============================================================
# DOMINIOS DE MÉTRICAS
# ============================================================
JNE_METRIC_IDS = set([c for c in JNE_DEP.columns if c in METRIC_IDS])
INDEX_METRIC_IDS = {"indice_habilitante_liderazgo_femenino_0_100"}
ENAHO_METRIC_IDS = set(METRIC_IDS) - JNE_METRIC_IDS - INDEX_METRIC_IDS

# ============================================================
# MAPA ROBUSTO CON PLOTLY
# ============================================================
def build_map_figure(dep_year, metric_id, mode, dep_focus):
    dep_year = dep_year.copy()
    value_col = metric_id if mode == "raw" else f"{metric_id}_anom_nat"
    sample_col = pick_sample_column(metric_id)

    needed = ["departamento", "lat", "lon", value_col]
    needed = [c for c in needed if c in dep_year.columns]
    dfm = dep_year[needed + ([sample_col] if sample_col in dep_year.columns else [])].copy()

    if "lat" not in dfm.columns or "lon" not in dfm.columns:
        return make_info_figure("Mapa territorial", "No hay coordenadas para graficar el mapa.")

    dfm[value_col] = pd.to_numeric(dfm[value_col], errors="coerce")
    dfm["lat"] = pd.to_numeric(dfm["lat"], errors="coerce")
    dfm["lon"] = pd.to_numeric(dfm["lon"], errors="coerce")

    if sample_col in dfm.columns:
        dfm[sample_col] = pd.to_numeric(dfm[sample_col], errors="coerce").fillna(1)
    else:
        dfm[sample_col] = 1

    dfm = dfm.dropna(subset=["lat", "lon", value_col])

    if dfm.empty:
        return make_info_figure("Mapa territorial", "No hay datos válidos para el mapa.")

    vals = dfm[value_col].dropna()
    if len(vals) == 0:
        vmin, vmax = -1, 1
    else:
        vmin = np.nanpercentile(vals, 5)
        vmax = np.nanpercentile(vals, 95)
        if is_diverging_metric(metric_id, mode):
            vmax_abs = max(abs(vmin), abs(vmax), 1e-9)
            vmin, vmax = -vmax_abs, vmax_abs

    scale = "RdPu"
    midpoint = None
    if is_diverging_metric(metric_id, mode):
        scale = "RdBu_r"
        midpoint = 0

    fig = px.scatter_geo(
        dfm,
        lat="lat",
        lon="lon",
        color=value_col,
        size=sample_col,
        hover_name="departamento",
        custom_data=["departamento", value_col],
        color_continuous_scale=scale,
        color_continuous_midpoint=midpoint,
        size_max=24,
        projection="mercator",
    )

    focus_df = dfm[dfm["departamento"].astype(str) == str(dep_focus)].copy()
    if not focus_df.empty:
        fig.add_trace(
            go.Scattergeo(
                lon=focus_df["lon"],
                lat=focus_df["lat"],
                mode="markers+text",
                text=focus_df["departamento"],
                textposition="top center",
                marker=dict(
                    size=28,
                    color="rgba(0,0,0,0)",
                    line=dict(color=TEXT, width=3),
                    symbol="circle",
                ),
                showlegend=False,
                hoverinfo="skip",
            )
        )

    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            + metric_label(metric_id)
            + ": %{customdata[1]:.4f}<extra></extra>"
        )
    )

    fig.update_geos(
        lataxis_range=[-19.5, 1.5],
        lonaxis_range=[-82.5, -67.0],
        showland=True,
        landcolor="#f2f2f2",
        showcountries=True,
        countrycolor="rgba(120,120,120,0.35)",
        showcoastlines=True,
        coastlinecolor="rgba(120,120,120,0.4)",
        bgcolor=CARD,
        resolution=50,
    )

    fig.update_layout(
        title=f"Mapa territorial · {metric_label(metric_id)}",
        template="plotly_white",
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font={"family": "Arial", "color": TEXT},
        margin=dict(l=10, r=10, t=55, b=10),
        coloraxis_colorbar=dict(title=metric_label(metric_id)),
        clickmode="event+select",
    )
    return fig

# ============================================================
# APP
# ============================================================
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
server = app.server
app.title = "Brecha de género, cuidados y liderazgo político"

# ============================================================
# LAYOUT
# ============================================================
app.layout = dbc.Container(
    [
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.I(className="bi bi-stars", style={"fontSize": "1.5rem", "marginRight": "10px"}),
                                html.Span("Brecha de género, cuidados y liderazgo político", style={"fontWeight": "800", "fontSize": "1.9rem"}),
                            ],
                            style={"display": "flex", "alignItems": "center", "color": "white"},
                        ),
                        html.Div(
                            "ENAHO 2008–2024 + JNE · análisis territorial, socioeconómico y de representación femenina",
                            style={"color": "#f7ecfb", "fontSize": "1rem", "marginTop": "8px"},
                        ),
                    ],
                    style={
                        "padding": "24px",
                        "borderRadius": "26px",
                        "background": "linear-gradient(135deg, #8e24aa 0%, #d81b60 48%, #00acc1 100%)",
                        "boxShadow": "0 12px 30px rgba(142,36,170,0.20)",
                        "marginTop": "18px",
                        "marginBottom": "18px",
                    },
                ),
            ]
        ),

        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Div(
                                        [
                                            html.H4("Controles", className="fw-bold", style={"color": TEXT, "marginBottom": "2px"}),
                                            html.Div("Filtra ENAHO y cruza con liderazgo político del JNE.", style={"color": MUTED, "fontSize": "0.9rem"}),
                                        ],
                                        style={"marginBottom": "16px"},
                                    ),

                                    html.Label("Año", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="year-dd",
                                        options=[{"label": str(y), "value": y} for y in YEARS],
                                        value=DEFAULT_YEAR,
                                        clearable=False,
                                    ),

                                    html.Br(),
                                    html.Label("Grupo de métricas", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="metric-group-dd",
                                        options=[{"label": "Todas", "value": "Todas"}] + [{"label": g, "value": g} for g in METRIC_GROUPS],
                                        value="Todas",
                                        clearable=False,
                                    ),

                                    html.Br(),
                                    html.Label("Métrica principal", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="metric-dd",
                                        options=[{"label": r["label"], "value": r["id"]} for r in METRIC_OPTIONS],
                                        value=DEFAULT_METRIC if DEFAULT_METRIC in METRIC_MAP else METRIC_OPTIONS[0]["id"],
                                        clearable=False,
                                    ),

                                    html.Br(),
                                    html.Label("Modo de visualización", className="fw-bold"),
                                    dcc.RadioItems(
                                        id="mode-radio",
                                        options=[
                                            {"label": " Valor observado", "value": "raw"},
                                            {"label": " Anomalía vs Perú", "value": "anom"},
                                        ],
                                        value="raw",
                                        inline=False,
                                        inputStyle={"marginRight": "6px"},
                                        labelStyle={"display": "block", "marginBottom": "6px"},
                                    ),

                                    html.Hr(),

                                    html.Label("Departamento destacado", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="dep-dd",
                                        options=[{"label": d, "value": d} for d in DEPARTMENTS],
                                        value=DEFAULT_DEPARTMENT if DEFAULT_DEPARTMENT in DEPARTMENTS else DEPARTMENTS[0],
                                        clearable=False,
                                    ),

                                    html.Br(),
                                    html.Label("Top N en ranking", className="fw-bold"),
                                    dcc.Slider(
                                        id="topn-slider",
                                        min=5,
                                        max=max(5, len(DEPARTMENTS)),
                                        step=1,
                                        value=12,
                                        marks={5: "5", 10: "10", 15: "15", 20: "20", 25: "25"},
                                    ),

                                    html.Hr(),

                                    html.Label("Clase social", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="class-dd",
                                        options=[{"label": "Todas", "value": "Todas"}] + [{"label": x, "value": x} for x in CLASS_OPTIONS],
                                        value="Todas",
                                        clearable=False,
                                    ),

                                    html.Br(),
                                    html.Label("Etnia", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="eth-dd",
                                        options=[{"label": "Todas", "value": "Todas"}] + [{"label": x, "value": x} for x in ETH_OPTIONS],
                                        value="Todas",
                                        clearable=False,
                                    ),

                                    html.Br(),
                                    html.Label("Ocupación", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="occ-dd",
                                        options=[{"label": "Todas", "value": "Todas"}] + [{"label": x, "value": x} for x in OCC_OPTIONS],
                                        value="Todas",
                                        clearable=False,
                                    ),

                                    html.Br(),
                                    html.Label("Grupo etario", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="age-dd",
                                        options=[{"label": "Todas", "value": "Todas"}] + [{"label": x, "value": x} for x in AGE_OPTIONS],
                                        value="Todas",
                                        clearable=False,
                                    ),

                                    html.Hr(),

                                    html.Label("Scatter · métrica X", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="scatter-x-dd",
                                        options=[{"label": r["label"], "value": r["id"]} for r in METRIC_OPTIONS],
                                        value="tasa_educ_sup_mujer" if "tasa_educ_sup_mujer" in METRIC_MAP else METRIC_OPTIONS[0]["id"],
                                        clearable=False,
                                    ),

                                    html.Br(),
                                    html.Label("Scatter · métrica Y", className="fw-bold"),
                                    dcc.Dropdown(
                                        id="scatter-y-dd",
                                        options=[{"label": r["label"], "value": r["id"]} for r in METRIC_OPTIONS],
                                        value="share_autoridades_mujeres" if "share_autoridades_mujeres" in METRIC_MAP else METRIC_OPTIONS[0]["id"],
                                        clearable=False,
                                    ),

                                    html.Hr(),

                                    dbc.Alert(
                                        [
                                            html.Div(html.B("Consejo"), className="mb-1"),
                                            html.Div(
                                                "Haz click sobre un punto del mapa para cambiar el departamento destacado."
                                            ),
                                        ],
                                        color="light",
                                        style={
                                            "borderRadius": "14px",
                                            "fontSize": "0.88rem",
                                            "border": f"1px solid {BORDER}",
                                            "background": SOFT2,
                                            "color": TEXT,
                                        },
                                    ),

                                    dbc.Alert(
                                        [
                                            html.Div(html.B("Nota metodológica"), className="mb-1"),
                                            html.Div(
                                                "Los filtros de clase, etnia, ocupación y edad recalculan las métricas ENAHO. "
                                                "Las métricas JNE reflejan autoridades electas y no cambian con esos filtros."
                                            ),
                                        ],
                                        color="light",
                                        style={
                                            "borderRadius": "14px",
                                            "fontSize": "0.88rem",
                                            "border": f"1px solid {BORDER}",
                                            "background": SOFT2,
                                            "color": TEXT,
                                        },
                                    ),
                                ]
                            ),
                            style={**card_style(), "position": "sticky", "top": "14px"},
                        ),
                    ],
                    md=3,
                ),

                dbc.Col(
                    [
                        html.Div(id="context-note", style={"marginBottom": "12px"}),
                        html.Div(id="metric-note", style={"marginBottom": "12px"}),
                        html.Div(id="general-reading-box", style={"marginBottom": "12px"}),
                        html.Div(id="metric-interpretation-box", style={"marginBottom": "16px"}),

                        html.Div(
                            id="kpi-row",
                            style={
                                "display": "grid",
                                "gridTemplateColumns": "repeat(auto-fit, minmax(220px, 1fr))",
                                "gap": "12px",
                                "marginBottom": "18px",
                            },
                        ),

                        dcc.Loading(
                            type="default",
                            color=PURPLE,
                            children=[
                                dbc.Tabs(
                                    [
                                        dbc.Tab(
                                            label="Territorio",
                                            children=[
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            dbc.Card(
                                                                dbc.CardBody([dcc.Graph(id="map-graph", style={"height": "630px"})]),
                                                                style=card_style(),
                                                            ),
                                                            md=7,
                                                        ),
                                                        dbc.Col(
                                                            [
                                                                dbc.Card(
                                                                    dbc.CardBody([dcc.Graph(id="line-chart")]),
                                                                    style={**card_style(), "marginBottom": "14px"},
                                                                ),
                                                                dbc.Card(
                                                                    dbc.CardBody([dcc.Graph(id="ranking-chart")]),
                                                                    style=card_style(),
                                                                ),
                                                            ],
                                                            md=5,
                                                        ),
                                                    ],
                                                    className="g-3",
                                                    style={"marginTop": "0px"},
                                                ),
                                            ],
                                        ),

                                        dbc.Tab(
                                            label="Cruces y relaciones",
                                            children=[
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            dbc.Card(
                                                                dbc.CardBody([dcc.Graph(id="scatter-chart")]),
                                                                style=card_style(),
                                                            ),
                                                            md=6,
                                                        ),
                                                        dbc.Col(
                                                            dbc.Card(
                                                                dbc.CardBody([dcc.Graph(id="corr-heatmap")]),
                                                                style=card_style(),
                                                            ),
                                                            md=6,
                                                        ),
                                                    ],
                                                    className="g-3",
                                                    style={"marginTop": "0px"},
                                                ),
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            dbc.Card(
                                                                dbc.CardBody([dcc.Graph(id="class-chart")]),
                                                                style=card_style(),
                                                            ),
                                                            md=4,
                                                        ),
                                                        dbc.Col(
                                                            dbc.Card(
                                                                dbc.CardBody([dcc.Graph(id="eth-chart")]),
                                                                style=card_style(),
                                                            ),
                                                            md=4,
                                                        ),
                                                        dbc.Col(
                                                            dbc.Card(
                                                                dbc.CardBody([dcc.Graph(id="occ-chart")]),
                                                                style=card_style(),
                                                            ),
                                                            md=4,
                                                        ),
                                                    ],
                                                    className="g-3",
                                                    style={"marginTop": "4px"},
                                                ),
                                            ],
                                        ),

                                        dbc.Tab(
                                            label="Tablas",
                                            children=[
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            dbc.Card(
                                                                dbc.CardBody(
                                                                    [
                                                                        html.H5("Tabla territorial del año", className="fw-bold"),
                                                                        dash_table.DataTable(
                                                                            id="table-dep",
                                                                            page_size=10,
                                                                            sort_action="native",
                                                                            filter_action="native",
                                                                            style_table={"overflowX": "auto"},
                                                                            style_header={"fontWeight": "700", "backgroundColor": "#f8ebfb"},
                                                                            style_cell={
                                                                                "fontFamily": "Arial",
                                                                                "fontSize": 13,
                                                                                "padding": "8px",
                                                                                "textAlign": "left",
                                                                                "whiteSpace": "normal",
                                                                                "height": "auto",
                                                                            },
                                                                        ),
                                                                    ]
                                                                ),
                                                                style=card_style(),
                                                            ),
                                                            md=7,
                                                        ),
                                                        dbc.Col(
                                                            dbc.Card(
                                                                dbc.CardBody(
                                                                    [
                                                                        html.H5("Consolidado 2008–2024", className="fw-bold"),
                                                                        dash_table.DataTable(
                                                                            id="table-all",
                                                                            page_size=10,
                                                                            sort_action="native",
                                                                            filter_action="native",
                                                                            style_table={"overflowX": "auto"},
                                                                            style_header={"fontWeight": "700", "backgroundColor": "#f8ebfb"},
                                                                            style_cell={
                                                                                "fontFamily": "Arial",
                                                                                "fontSize": 13,
                                                                                "padding": "8px",
                                                                                "textAlign": "left",
                                                                                "whiteSpace": "normal",
                                                                                "height": "auto",
                                                                            },
                                                                        ),
                                                                    ]
                                                                ),
                                                                style=card_style(),
                                                            ),
                                                            md=5,
                                                        ),
                                                    ],
                                                    className="g-3",
                                                    style={"marginTop": "0px"},
                                                ),
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            dbc.Card(
                                                                dbc.CardBody(
                                                                    [
                                                                        html.H5("Serie nacional y del departamento", className="fw-bold"),
                                                                        dash_table.DataTable(
                                                                            id="table-nat",
                                                                            page_size=10,
                                                                            sort_action="native",
                                                                            filter_action="native",
                                                                            style_table={"overflowX": "auto"},
                                                                            style_header={"fontWeight": "700", "backgroundColor": "#f8ebfb"},
                                                                            style_cell={
                                                                                "fontFamily": "Arial",
                                                                                "fontSize": 13,
                                                                                "padding": "8px",
                                                                                "textAlign": "left",
                                                                                "whiteSpace": "normal",
                                                                                "height": "auto",
                                                                            },
                                                                        ),
                                                                    ]
                                                                ),
                                                                style=card_style(),
                                                            ),
                                                            md=12,
                                                        ),
                                                    ],
                                                    className="g-3",
                                                    style={"marginTop": "4px"},
                                                ),
                                            ],
                                        ),

                                        dbc.Tab(
                                            label="Lectura metodológica",
                                            children=[
                                                dbc.Card(
                                                    dbc.CardBody(
                                                        [
                                                            html.H4("Cómo interpretar el dashboard", className="fw-bold"),
                                                            html.P(
                                                                "Este panel combina métricas de ENAHO con representación política del JNE. "
                                                                "Las métricas de tipo 'gap' y 'penalty' se leen respecto a cero; "
                                                                "las métricas de tipo 'ratio' se leen respecto a uno; "
                                                                "las métricas de representación femenina suelen usar 0.5 como referencia aproximada de paridad."
                                                            ),
                                                            html.Ul(
                                                                [
                                                                    html.Li("Gap cercano a 0: poca diferencia entre grupos."),
                                                                    html.Li("Ratio cercano a 1: relativa paridad."),
                                                                    html.Li("Representación femenina cercana a 0.5: referencia útil de equilibrio."),
                                                                    html.Li("Índice compuesto alto: entorno más habilitante para liderazgo femenino."),
                                                                ]
                                                            ),
                                                        ]
                                                    ),
                                                    style=card_style(),
                                                )
                                            ],
                                        ),
                                    ],
                                    style={"marginBottom": "22px"},
                                )
                            ],
                        ),
                    ],
                    md=9,
                ),
            ],
            className="g-3",
        ),
    ],
    fluid=True,
    style={"backgroundColor": BG, "minHeight": "100vh", "paddingBottom": "18px"},
)

# ============================================================
# CALLBACK: OPCIONES DE MÉTRICA
# ============================================================
@app.callback(
    Output("metric-dd", "options"),
    Output("metric-dd", "value"),
    Input("metric-group-dd", "value"),
    State("metric-dd", "value"),
)
def update_metric_options(selected_group, current_metric):
    rows = filter_metric_options_by_group(selected_group)
    options = [{"label": r["label"], "value": r["id"]} for r in rows]

    valid_ids = [r["id"] for r in rows]
    if current_metric in valid_ids:
        value = current_metric
    else:
        value = valid_ids[0] if len(valid_ids) > 0 else None

    return options, value

# ============================================================
# CALLBACK: CLICK EN MAPA -> DEPARTAMENTO
# ============================================================
@app.callback(
    Output("dep-dd", "value", allow_duplicate=True),
    Input("map-graph", "clickData"),
    State("dep-dd", "value"),
    prevent_initial_call=True,
)
def update_dep_from_map(clickData, current_dep):
    try:
        if not clickData:
            return no_update
        points = clickData.get("points", [])
        if len(points) == 0:
            return no_update

        pt = points[0]
        custom = pt.get("customdata", None)
        if custom and len(custom) >= 1:
            dep = str(custom[0])
            if dep in DEPARTMENTS:
                logger.info("Mapa click -> departamento=%s", dep)
                return dep
        return no_update
    except Exception as e:
        logger.exception("Error al leer clickData del mapa: %s", e)
        return no_update

# ============================================================
# CALLBACK PRINCIPAL
# ============================================================
@app.callback(
    Output("context-note", "children"),
    Output("metric-note", "children"),
    Output("general-reading-box", "children"),
    Output("metric-interpretation-box", "children"),
    Output("kpi-row", "children"),
    Output("map-graph", "figure"),
    Output("line-chart", "figure"),
    Output("ranking-chart", "figure"),
    Output("scatter-chart", "figure"),
    Output("corr-heatmap", "figure"),
    Output("class-chart", "figure"),
    Output("eth-chart", "figure"),
    Output("occ-chart", "figure"),
    Output("table-dep", "data"),
    Output("table-dep", "columns"),
    Output("table-all", "data"),
    Output("table-all", "columns"),
    Output("table-nat", "data"),
    Output("table-nat", "columns"),
    Input("year-dd", "value"),
    Input("metric-dd", "value"),
    Input("mode-radio", "value"),
    Input("dep-dd", "value"),
    Input("class-dd", "value"),
    Input("eth-dd", "value"),
    Input("occ-dd", "value"),
    Input("age-dd", "value"),
    Input("scatter-x-dd", "value"),
    Input("scatter-y-dd", "value"),
    Input("topn-slider", "value"),
)
def update_all(year, metric_id, mode, dep_focus, clase, etnia, ocupacion, grupo_edad, scatter_x, scatter_y, topn):
    try:
        logger.info(
            "CALLBACK update_all | year=%s metric=%s mode=%s dep=%s clase=%s etnia=%s ocupacion=%s grupo_edad=%s scatter_x=%s scatter_y=%s topn=%s",
            year, metric_id, mode, dep_focus, clase, etnia, ocupacion, grupo_edad, scatter_x, scatter_y, topn
        )

        cache = cached_compute_tables(
            str(clase),
            str(etnia),
            str(ocupacion),
            str(grupo_edad),
        )

        dep_df = read_json_df(cache["dep_integrated"])
        nat_df = read_json_df(cache["nat_integrated"])
        dep_all_df = read_json_df(cache["dep_integrated_all"])
        nat_all_df = read_json_df(cache["nat_integrated_all"])

        dep_df = normalize_dep_fields(dep_df, dep_col="dep_cod", dep_name_col="departamento")
        dep_all_df = normalize_dep_fields(dep_all_df, dep_col="dep_cod", dep_name_col="departamento")
        dep_df = normalize_year_col(dep_df, "anio")
        nat_df = normalize_year_col(nat_df, "anio")

        dep_df = ensure_unique_columns(dep_df, "callback_dep_df")
        nat_df = ensure_unique_columns(nat_df, "callback_nat_df")
        dep_all_df = ensure_unique_columns(dep_all_df, "callback_dep_all_df")
        nat_all_df = ensure_unique_columns(nat_all_df, "callback_nat_all_df")

        log_df_info("callback_dep_df", dep_df)
        log_df_info("callback_nat_df", nat_df)

        if dep_df.empty or nat_df.empty:
            empty_fig = make_info_figure("Sin datos", "No hay observaciones con los filtros seleccionados.")
            return (
                dbc.Alert("Sin datos para los filtros seleccionados.", color="warning"),
                dbc.Card(dbc.CardBody("Sin datos"), style=card_style()),
                dbc.Alert("Sin datos.", color="warning"),
                dbc.Card(dbc.CardBody("Sin datos"), style=card_style()),
                [make_kpi_card("Sin datos", "NA", "", "bi bi-exclamation-triangle")],
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                [],
                [],
                [],
                [],
                [],
                [],
            )

        dep_year = dep_df[dep_df["anio"] == int(year)].copy()
        nat_year = nat_df[nat_df["anio"] == int(year)].copy()

        if dep_year.empty or nat_year.empty:
            empty_fig = make_info_figure("Sin datos", f"No hay datos para el año {year}.")
            return (
                dbc.Alert(f"No hay datos para el año {year}.", color="warning"),
                dbc.Card(dbc.CardBody("Sin datos"), style=card_style()),
                dbc.Alert("Sin datos.", color="warning"),
                dbc.Card(dbc.CardBody("Sin datos"), style=card_style()),
                [make_kpi_card("Sin datos", "NA", "", "bi bi-exclamation-triangle")],
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                [],
                [],
                [],
                [],
                [],
                [],
            )

        if dep_focus not in dep_year["departamento"].astype(str).tolist():
            dep_focus = dep_year["departamento"].astype(str).iloc[0]

        focus_row = dep_year[dep_year["departamento"].astype(str) == str(dep_focus)].iloc[0]
        nat_row = nat_year.iloc[0]

        if metric_id in JNE_METRIC_IDS:
            context_note = dbc.Alert(
                [
                    html.Div(html.B("Métrica política del JNE"), className="mb-1"),
                    html.Div(
                        "La métrica seleccionada proviene de autoridades electas. "
                        "Los filtros socioeconómicos recalculan ENAHO, pero no alteran directamente esta métrica."
                    ),
                ],
                color="info",
                style={"borderRadius": "16px", "border": f"1px solid {BORDER}"},
            )
        elif metric_id in INDEX_METRIC_IDS:
            context_note = dbc.Alert(
                [
                    html.Div(html.B("Índice compuesto integrado"), className="mb-1"),
                    html.Div(
                        "Este índice combina variables ENAHO filtradas con la representación política femenina del JNE. "
                        "Por eso su valor sí cambia cuando cambian los filtros ENAHO."
                    ),
                ],
                color="secondary",
                style={"borderRadius": "16px", "border": f"1px solid {BORDER}"},
            )
        else:
            context_note = dbc.Alert(
                [
                    html.Div(html.B("Métrica socioeconómica ENAHO"), className="mb-1"),
                    html.Div(
                        "La métrica seleccionada se recalcula con los filtros activos y se compara territorialmente para el año seleccionado."
                    ),
                ],
                color="light",
                style={"borderRadius": "16px", "border": f"1px solid {BORDER}"},
            )

        metric_note = dbc.Card(
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.Div(
                                html.Span(metric_group(metric_id), style={
                                    "background": SOFT,
                                    "color": PURPLE,
                                    "padding": "5px 10px",
                                    "borderRadius": "999px",
                                    "fontWeight": "700",
                                    "fontSize": "0.78rem",
                                }),
                                style={"marginBottom": "10px"},
                            ),
                            html.H4(metric_label(metric_id), className="fw-bold", style={"marginBottom": "4px", "color": TEXT}),
                            html.Div(
                                f"Tipo: {metric_type(metric_id)} · Unidad: {metric_unit(metric_id)}",
                                style={"color": MUTED, "fontSize": "0.92rem"},
                            ),
                        ]
                    )
                ]
            ),
            style=card_style(),
        )

        value_col = metric_id if mode == "raw" else f"{metric_id}_anom_nat"

        if value_col not in dep_year.columns:
            empty_fig = make_info_figure("Sin datos", f"La métrica {metric_id} no está disponible para este subconjunto.")
            return (
                context_note,
                metric_note,
                dbc.Alert("Métrica no disponible.", color="warning"),
                build_metric_interpretation_card(metric_id, np.nan, np.nan, np.nan, dep_focus),
                [make_kpi_card("Métrica no disponible", "NA", metric_label(metric_id), "bi bi-exclamation-circle")],
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                empty_fig,
                [],
                [],
                [],
                [],
                [],
                [],
            )

        vals = pd.to_numeric(dep_year[value_col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(vals) == 0:
            vmin, vmax = -1, 1
        else:
            vmin = np.nanpercentile(vals, 5)
            vmax = np.nanpercentile(vals, 95)
            if is_diverging_metric(metric_id, mode):
                vmax_abs = max(abs(vmin), abs(vmax), 1e-9)
                vmin, vmax = -vmax_abs, vmax_abs

        sample_col = pick_sample_column(metric_id)
        best_row = dep_year.loc[pd.to_numeric(dep_year[value_col], errors="coerce").idxmax()] if dep_year[value_col].notna().any() else focus_row

        rank_df_valid = dep_year[["departamento", value_col]].copy()
        rank_df_valid[value_col] = pd.to_numeric(rank_df_valid[value_col], errors="coerce")
        rank_df_valid = rank_df_valid.dropna(subset=[value_col]).sort_values(value_col, ascending=False).reset_index(drop=True)

        if dep_focus in rank_df_valid["departamento"].astype(str).tolist():
            focus_rank = int(rank_df_valid.index[rank_df_valid["departamento"].astype(str) == str(dep_focus)][0] + 1)
            rank_text = f"puesto {focus_rank} de {len(rank_df_valid)}"
        else:
            rank_text = "sin ranking disponible"

        focus_val = focus_row.get(metric_id, np.nan)
        nat_val = nat_row.get(metric_id, np.nan)
        anom_val = focus_row.get(f"{metric_id}_anom_nat", np.nan)

        general_reading = build_general_reading(
            metric_id=metric_id,
            dep_name=dep_focus,
            dep_value=focus_val,
            nat_value=nat_val,
            anom_value=anom_val,
            best_dep=str(best_row["departamento"]),
            best_value=best_row.get(metric_id, np.nan),
            rank_text=rank_text,
        )

        metric_interpretation = build_metric_interpretation_card(
            metric_id=metric_id,
            focus_val=focus_val,
            nat_val=nat_val,
            anom_val=anom_val,
            dep_name=dep_focus,
        )

        kpis = [
            make_kpi_card(
                "Valor del departamento",
                fmt_value(focus_val, metric_id),
                dep_focus,
                "bi bi-geo-alt-fill"
            ),
            make_kpi_card(
                "Anomalía vs Perú",
                fmt_value(anom_val, metric_id),
                "Departamento - nacional",
                "bi bi-globe-americas"
            ),
            make_kpi_card(
                "Valor nacional",
                fmt_value(nat_val, metric_id),
                metric_label(metric_id),
                "bi bi-flag-fill"
            ),
            make_kpi_card(
                "Ranking territorial",
                rank_text.replace("puesto ", "#"),
                metric_label(metric_id),
                "bi bi-trophy-fill"
            ),
            make_kpi_card(
                "Máximo territorial",
                str(best_row["departamento"]),
                fmt_value(best_row.get(metric_id, np.nan), metric_id),
                "bi bi-arrow-up-circle-fill"
            ),
            make_kpi_card(
                "Tamaño muestral / universo",
                fmt_simple(focus_row.get(sample_col, np.nan)),
                sample_col,
                "bi bi-people-fill"
            ),
        ]

        # --------------------------------------------------------
        # MAPA NUEVO ROBUSTO
        # --------------------------------------------------------
        fig_map = build_map_figure(dep_year, metric_id, mode, dep_focus)

        # --------------------------------------------------------
        # SERIE TEMPORAL
        # --------------------------------------------------------
        dep_series = dep_df[dep_df["departamento"].astype(str) == str(dep_focus)].copy()
        nat_series = nat_df.copy()

        fig_line = go.Figure()
        fig_line.add_trace(
            go.Scatter(
                x=nat_series["anio"],
                y=nat_series[metric_id] if metric_id in nat_series.columns else [np.nan] * len(nat_series),
                mode="lines+markers",
                name="Perú",
                line=dict(color=PURPLE, width=4),
                marker=dict(size=7),
            )
        )
        fig_line.add_trace(
            go.Scatter(
                x=dep_series["anio"],
                y=dep_series[metric_id] if metric_id in dep_series.columns else [np.nan] * len(dep_series),
                mode="lines+markers",
                name=dep_focus,
                line=dict(color=CYAN, width=4),
                marker=dict(size=7),
            )
        )
        fig_line = figure_layout(fig_line, f"Tendencia temporal · {metric_label(metric_id)}")

        # --------------------------------------------------------
        # RANKING
        # --------------------------------------------------------
        rank_df = dep_year.copy()
        rank_df[value_col] = pd.to_numeric(rank_df[value_col], errors="coerce")
        rank_df = rank_df.dropna(subset=[value_col]).sort_values(value_col, ascending=False).head(int(topn))

        if rank_df.empty:
            fig_rank = make_info_figure("Ranking", "Sin datos para construir el ranking.")
        else:
            rank_df["grupo_color"] = np.where(rank_df["departamento"].astype(str) == str(dep_focus), "Destacado", "Resto")
            fig_rank = px.bar(
                rank_df.sort_values(value_col, ascending=True),
                x=value_col,
                y="departamento",
                orientation="h",
                color="grupo_color",
                color_discrete_map={"Destacado": PINK, "Resto": PURPLE},
                title=f"Top {int(topn)} territorial · {metric_label(metric_id)}",
            )
            fig_rank = figure_layout(fig_rank)

        # --------------------------------------------------------
        # SCATTER
        # --------------------------------------------------------
        if scatter_x not in dep_year.columns or scatter_y not in dep_year.columns:
            fig_scatter = make_info_figure("Relación entre variables", "Selecciona métricas disponibles para el scatter.")
        else:
            scat = dep_year[["departamento", scatter_x, scatter_y]].copy()
            scat = ensure_unique_columns(scat, "scatter_df")
            scat[scatter_x] = pd.to_numeric(scat[scatter_x], errors="coerce")
            scat[scatter_y] = pd.to_numeric(scat[scatter_y], errors="coerce")
            scat = scat.dropna(subset=[scatter_x, scatter_y])

            if scat.empty:
                fig_scatter = make_info_figure("Relación entre variables", "No hay datos suficientes para el scatter.")
            else:
                scat["destacado"] = np.where(scat["departamento"].astype(str) == str(dep_focus), "Departamento destacado", "Otros")
                fig_scatter = px.scatter(
                    scat,
                    x=scatter_x,
                    y=scatter_y,
                    color="destacado",
                    color_discrete_map={"Departamento destacado": PINK, "Otros": CYAN},
                    hover_name="departamento",
                    title=f"Relación territorial · {year}",
                    labels={
                        scatter_x: metric_label(scatter_x),
                        scatter_y: metric_label(scatter_y),
                    },
                )

                if len(scat) >= 2:
                    xx = scat[scatter_x].to_numpy()
                    yy = scat[scatter_y].to_numpy()
                    try:
                        coef = np.polyfit(xx, yy, 1)
                        xline = np.linspace(np.nanmin(xx), np.nanmax(xx), 100)
                        yline = coef[0] * xline + coef[1]
                        fig_scatter.add_trace(
                            go.Scatter(
                                x=xline,
                                y=yline,
                                mode="lines",
                                name="Tendencia",
                                line=dict(color=TEXT, dash="dash", width=2),
                            )
                        )
                    except Exception:
                        logger.warning("No se pudo ajustar tendencia en scatter.")

                fig_scatter = figure_layout(
                    fig_scatter,
                    f"Scatter territorial · {metric_label(scatter_x)} vs {metric_label(scatter_y)}"
                )

        # --------------------------------------------------------
        # HEATMAP
        # --------------------------------------------------------
        corr_metrics = [
            "tasa_educ_sup_mujer",
            "ratio_trabajo_m_h",
            "gap_pobreza_m_h",
            "penalidad_maternidad_trabajo",
            "share_autoridades_mujeres",
            "share_liderazgo_ejecutivo_mujeres",
            "indice_habilitante_liderazgo_femenino_0_100",
        ]
        corr_metrics = [m for m in corr_metrics if m in dep_year.columns]

        if len(corr_metrics) < 2:
            fig_corr = make_info_figure("Correlaciones clave", "No hay suficientes variables disponibles para la matriz.")
        else:
            corr_df = dep_year[corr_metrics].apply(pd.to_numeric, errors="coerce")
            corr = corr_df.corr(numeric_only=True)
            label_map = {m: metric_label(m) for m in corr.columns}

            fig_corr = px.imshow(
                corr.rename(index=label_map, columns=label_map),
                text_auto=".2f",
                color_continuous_scale="RdBu_r",
                zmin=-1, zmax=1,
                title=f"Correlaciones entre variables clave · {year}"
            )
            fig_corr = figure_layout(fig_corr)
            fig_corr.update_layout(coloraxis_colorbar=dict(title="r"))

        # --------------------------------------------------------
        # CRUCES POR GRUPO
        # --------------------------------------------------------
        df_year = apply_filters_enaho(
            DF[pd.to_numeric(DF["ANIO_ENCUESTA"], errors="coerce") == int(year)].copy(),
            clase=clase,
            etnia=etnia,
            ocupacion=ocupacion,
            grupo_edad=grupo_edad,
        )
        df_year_dep = df_year[df_year["DEPARTAMENTO"].astype(str) == str(dep_focus)].copy()

        def group_chart(by_col, title_prefix):
            if metric_id not in ENAHO_METRIC_IDS:
                return make_info_figure(
                    title_prefix,
                    "Los cruces por grupos solo aplican a métricas derivadas de ENAHO."
                )

            tab = build_group_table(df_year_dep, by_col)
            if tab.empty or metric_id not in tab.columns:
                return make_info_figure(title_prefix, "Sin datos para este cruce.")

            tab[metric_id] = pd.to_numeric(tab[metric_id], errors="coerce")
            tab = tab.dropna(subset=[metric_id])

            if tab.empty:
                return make_info_figure(title_prefix, "Sin datos para este cruce.")

            fig = px.bar(
                tab.sort_values(metric_id, ascending=False),
                x=by_col,
                y=metric_id,
                color=metric_id,
                color_continuous_scale=["#00acc1", "#f6eff7", "#d81b60"] if metric_type(metric_id) in {"gap", "penalty"} else ["#f8c7dc", "#8e24aa"],
                title=f"{dep_focus} · {metric_label(metric_id)} por {title_prefix.lower()}",
            )
            fig.update_layout(coloraxis_showscale=False)
            return figure_layout(fig)

        fig_class = group_chart("CLASE_SOCIAL_PROXY", "Clase social")
        fig_eth = group_chart("ETNIA_GRUPO", "Etnia")
        fig_occ = group_chart("OCUPACION_GRUPO", "Ocupación")

        # --------------------------------------------------------
        # TABLAS
        # --------------------------------------------------------
        show_cols_dep = unique_preserve_order([
            "departamento",
            metric_id,
            f"{metric_id}_anom_nat",
            "tasa_educ_sup_mujer",
            "gap_trabaja_horas_h_m",
            "gap_horas_h_m",
            "gap_pobreza_m_h",
            "penalidad_maternidad_trabajo",
            "share_autoridades_mujeres",
            "share_liderazgo_ejecutivo_mujeres",
            "indice_habilitante_liderazgo_femenino_0_100",
        ])
        show_cols_dep = [c for c in show_cols_dep if c in dep_year.columns]

        table_dep_df = dep_year[show_cols_dep].copy()
        table_dep_df = ensure_unique_columns(table_dep_df, "table_dep_df")

        for c in table_dep_df.columns:
            if c != "departamento":
                base_metric = metric_id if c == f"{metric_id}_anom_nat" else c
                if base_metric in METRIC_MAP:
                    table_dep_df[c] = table_format_series(table_dep_df[c], base_metric)

        table_dep = table_dep_df.to_dict("records")
        table_dep_cols = [{"name": c, "id": c} for c in table_dep_df.columns]

        show_cols_all = unique_preserve_order([
            "departamento",
            metric_id,
            "tasa_educ_sup_mujer",
            "gap_trabaja_horas_h_m",
            "gap_pobreza_m_h",
            "penalidad_maternidad_trabajo",
            "share_autoridades_mujeres",
            "share_liderazgo_ejecutivo_mujeres",
            "indice_habilitante_liderazgo_femenino_0_100",
        ])
        show_cols_all = [c for c in show_cols_all if c in dep_all_df.columns]

        table_all_df = dep_all_df[show_cols_all].copy() if not dep_all_df.empty else pd.DataFrame()
        table_all_df = ensure_unique_columns(table_all_df, "table_all_df")

        if not table_all_df.empty:
            for c in table_all_df.columns:
                if c != "departamento" and c in METRIC_MAP:
                    table_all_df[c] = table_format_series(table_all_df[c], c)

        table_all = table_all_df.to_dict("records") if not table_all_df.empty else []
        table_all_cols = [{"name": c, "id": c} for c in table_all_df.columns] if not table_all_df.empty else []

        nat_table_df = nat_df[["anio"]].copy()
        nat_table_df = ensure_unique_columns(nat_table_df, "nat_table_df_base")
        if metric_id in nat_df.columns:
            nat_table_df["Perú"] = table_format_series(nat_df[metric_id], metric_id)
        else:
            nat_table_df["Perú"] = "NA"

        dep_series_match = dep_df[dep_df["departamento"].astype(str) == str(dep_focus)][["anio"]].copy()
        dep_series_match = ensure_unique_columns(dep_series_match, "dep_series_match")

        if metric_id in dep_df.columns:
            dep_series_match[dep_focus] = table_format_series(
                dep_df[dep_df["departamento"].astype(str) == str(dep_focus)][metric_id],
                metric_id
            )
        else:
            dep_series_match[dep_focus] = "NA"

        if f"{metric_id}_anom_nat" in dep_df.columns:
            dep_series_match["Anomalía vs Perú"] = table_format_series(
                dep_df[dep_df["departamento"].astype(str) == str(dep_focus)][f"{metric_id}_anom_nat"],
                metric_id
            )
        else:
            dep_series_match["Anomalía vs Perú"] = "NA"

        nat_table_df = nat_table_df.merge(dep_series_match, on="anio", how="left")
        nat_table_df = ensure_unique_columns(nat_table_df, "nat_table_df_final")

        table_nat = nat_table_df.to_dict("records")
        table_nat_cols = [{"name": c, "id": c} for c in nat_table_df.columns]

        return (
            context_note,
            metric_note,
            general_reading,
            metric_interpretation,
            kpis,
            fig_map,
            fig_line,
            fig_rank,
            fig_scatter,
            fig_corr,
            fig_class,
            fig_eth,
            fig_occ,
            table_dep,
            table_dep_cols,
            table_all,
            table_all_cols,
            table_nat,
            table_nat_cols,
        )

    except Exception as e:
        logger.exception("ERROR en update_all: %s", e)
        err_txt = f"{type(e).__name__}: {e}"
        details = traceback.format_exc(limit=8)

        error_alert = dbc.Alert(
            [
                html.Div(html.B("Error en callback del dashboard"), className="mb-2"),
                html.Div(err_txt, className="mb-2"),
                html.Pre(details, style={"whiteSpace": "pre-wrap", "fontSize": "0.8rem", "margin": 0}),
            ],
            color="danger",
            style={"borderRadius": "16px"},
        )

        empty_fig = make_info_figure("Error", err_txt)

        return (
            error_alert,
            dbc.Card(dbc.CardBody("Revisa el log del servidor para más detalle."), style=card_style()),
            dbc.Alert("Error en lectura general.", color="danger"),
            dbc.Card(dbc.CardBody("Error en explicación de métrica."), style=card_style()),
            [make_kpi_card("Error", "NA", err_txt, "bi bi-bug-fill")],
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            empty_fig,
            [],
            [],
            [],
            [],
            [],
            [],
        )

if __name__ == "__main__":
    logger.info("Iniciando app Dash en 0.0.0.0:%s", PORT)
    app.run(debug=True, host="0.0.0.0", port=PORT)
