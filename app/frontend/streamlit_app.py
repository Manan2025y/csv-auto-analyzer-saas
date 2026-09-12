"""Professional Streamlit client for CSV Auto-Analyzer Global SaaS."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# SIMPLE PASSWORD PROTECTION
# ============================================================

def check_password():
    """Returns True if the user entered the correct password."""

    def password_entered():
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input(
            "Enter password", type="password",
            on_change=password_entered, key="password"
        )
        return False

    elif not st.session_state["password_correct"]:
        st.text_input(
            "Enter password", type="password",
            on_change=password_entered, key="password"
        )
        st.error("😕 Incorrect password")
        return False

    else:
        return True


if not check_password():
    st.stop()

# Find the project root so the backend packages can be imported reliably.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.backend.analysis.engine import analyze, to_numeric_series
from app.backend.analysis.qa import answer_question
from app.backend.currency import CURRENCIES, format_currency
from app.backend.ecommerce.rules import detect_ecommerce_platform
from app.backend.forecasting.engine import forecast_series
from app.backend.reports.excel_report import excel_report
from app.backend.reports.pdf_report import pdf_report
from app.backend.storage import delete_dashboard,list_dashboards,load_dashboard,save_dashboard
from app.frontend.charts import CHART_PALETTES,CHART_TYPES,automatic_chart_suggestions,build_chart,numeric_columns,prepare_chart_data

st.set_page_config(
    page_title="CSV Auto-Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

DEFAULTS = {
    "currency": "USD",
    "theme": "Day",
    "dashboard_bg": "#FFF8E1",
    "card_bg": "#FFFDF5",
    "chart_bg": "#FFFDF5",
    "df": None,
    "filename": "",
    "analysis": None,
    "dashboard_items": None,
    "kpi_items": None,
    "filters": {},
    # NEW: controls for the "same colour for every KPI" toggle in KPI Studio.
    "kpi_uniform_color": False,
    "kpi_shared_bg": None,  # resolved lazily to the current theme's card colour
}
for k,v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k]=v

THEMES = {
    # Light theme: warm, professional and easy on the eyes.
    "Day": {
        "app": "#FFF8E1",
        "surface": "#FFFDF5",
        "text": "#2B261C",
        "muted": "#665D4D",
        "border": "#E8DFC5",
        "dashboard": "#FFF8E1",
        "card": "#FFFDF5",
        "chart": "#FFFDF5",
    },

    # Dark theme: blue-black surfaces with bright text and clear borders.
    "Night": {
        "app": "#08111F",
        "surface": "#111C2E",
        "text": "#F4F7FF",
        "muted": "#B9C5D8",
        "border": "#2B3A50",
        "dashboard": "#0D1829",
        "card": "#132238",
        "chart": "#132238",
    },

    # A softer light option for users who do not want the warm Day theme.
    "Soft Light": {
        "app": "#F7F3EA",
        "surface": "#FFFFFF",
        "text": "#292524",
        "muted": "#6B625A",
        "border": "#E0D7C8",
        "dashboard": "#F7F3EA",
        "card": "#FFFFFF",
        "chart": "#FFFFFF",
    },

    # Darker blue option with slightly brighter blue surfaces.
    "Midnight Blue": {
        "app": "#071426",
        "surface": "#0D2039",
        "text": "#EAF3FF",
        "muted": "#A9BED8",
        "border": "#284564",
        "dashboard": "#0A1A2E",
        "card": "#102844",
        "chart": "#102844",
    },
}


# ============================================================
# NEW: keep KPI card colours in sync with the active theme
# ============================================================
def sync_kpi_backgrounds(old_theme: str, new_theme: str) -> None:
    """Move KPI card backgrounds over to the new theme's default colour.

    KPI cards remember their own "background" once they've been shown in
    KPI Studio (see the colour picker there). Without this helper, a KPI
    that is still using the *previous* theme's default card colour would
    stay stuck on that colour forever — e.g. staying white after switching
    from Day to Night. We only touch KPIs that are still on the OLD
    theme's default; a KPI where the user deliberately chose a custom
    colour is left completely untouched, mirroring how dashboard_bg /
    card_bg / chart_bg already behave above.
    """
    old_default = THEMES[old_theme]["card"]
    new_default = THEMES[new_theme]["card"]

    for collection_name in ("kpi_items", "dashboard_kpis"):
        collection = st.session_state.get(collection_name) or []
        for kpi in collection:
            if not isinstance(kpi, dict):
                continue
            # Treat "no background set yet" the same as "still on default".
            if kpi.get("background", old_default) == old_default:
                kpi["background"] = new_default

    # If the shared "uniform colour" picker was still on the old default,
    # move it forward too so the shared swatch reflects the new theme.
    if st.session_state.get("kpi_shared_bg") in (None, old_default):
        st.session_state.kpi_shared_bg = new_default


def sync_theme_from_settings():
    """Same theme handling for the Settings page.

    The sidebar and Settings page use different Streamlit widget keys. This
    function keeps the theme logic in one place while still preserving any
    custom colours chosen by the user.
    """
    old_theme = st.session_state.get("theme", "Day")
    new_theme = st.session_state.get("settings_theme", old_theme)

    if old_theme == new_theme:
        return

    old_defaults = THEMES[old_theme]
    new_defaults = THEMES[new_theme]

    for state_key, colour_key in (
        ("dashboard_bg", "dashboard"),
        ("card_bg", "card"),
        ("chart_bg", "chart"),
    ):
        if st.session_state.get(state_key) == old_defaults[colour_key]:
            st.session_state[state_key] = new_defaults[colour_key]

    # NEW: also carry KPI card backgrounds over to the new theme.
    sync_kpi_backgrounds(old_theme, new_theme)

    st.session_state.theme = new_theme


def sync_theme_from_widget():
    """Apply a theme change without destroying a user's custom colours.

    If the user is still using the previous theme's default dashboard/card/chart
    colours, we replace those defaults with the new theme's defaults. If the
    user deliberately picked a custom colour, we leave it untouched.
    """
    old_theme = st.session_state.get("theme", "Day")
    new_theme = st.session_state.get("sidebar_theme", old_theme)

    if old_theme == new_theme:
        return

    old_defaults = THEMES[old_theme]
    new_defaults = THEMES[new_theme]

    for state_key, colour_key in (
        ("dashboard_bg", "dashboard"),
        ("card_bg", "card"),
        ("chart_bg", "chart"),
    ):
        # Only replace a colour when it was still the old theme's default.
        # This protects custom colours selected by the user.
        if st.session_state.get(state_key) == old_defaults[colour_key]:
            st.session_state[state_key] = new_defaults[colour_key]

    # NEW: also carry KPI card backgrounds over to the new theme.
    sync_kpi_backgrounds(old_theme, new_theme)

    st.session_state.theme = new_theme


def apply_theme():
    """Inject the theme CSS used by the entire Streamlit application.

    Streamlit widgets are built with BaseWeb and several widgets use their own
    internal elements. Therefore we style the actual widget containers rather
    than relying only on `.stApp` text inheritance.
    """
    theme_name = st.session_state.get("theme", "Day")
    th = THEMES[theme_name]
    is_dark = theme_name in {"Night", "Midnight Blue"}
    color_scheme = "dark" if is_dark else "light"

    st.markdown(
        f"""
        <style>
        /* ==========================================================
           1. GLOBAL APPLICATION COLOURS
           ========================================================== */
        :root {{
            color-scheme: {color_scheme};
        }}

        html, body, [data-testid="stAppViewContainer"] {{
            background: {th['app']} !important;
        }}

        .stApp {{
            background: {th['app']} !important;
            color: {th['text']} !important;
        }}

        .block-container {{
            max-width: 1600px;
            padding-top: 1rem;
            padding-bottom: 4rem;
        }}

        /* ==========================================================
           2. SIDEBAR AND STREAMLIT TOP BAR
           ========================================================== */
        [data-testid="stSidebar"] {{
            background: {th['surface']} !important;
            border-right: 1px solid {th['border']} !important;
        }}

        [data-testid="stSidebar"] > div:first-child {{
            background: {th['surface']} !important;
        }}

        [data-testid="stHeader"],
        header[data-testid="stHeader"] {{
            background: {th['app']} !important;
        }}

        [data-testid="stToolbar"] {{
            background: transparent !important;
        }}

        /* ==========================================================
           3. NORMAL TEXT
           Avoid styling every <span>, because Streamlit uses spans
           internally for icons and widget implementation details.
           ========================================================== */
        h1, h2, h3, h4, h5, h6,
        p, label, li,
        [data-testid="stMarkdownContainer"] {{
            color: {th['text']} !important;
        }}

        [data-testid="stCaptionContainer"] {{
            color: {th['muted']} !important;
        }}

        .small {{
            color: {th['muted']} !important;
            font-size: 0.86rem;
        }}

        /* ==========================================================
           4. BUTTONS
           The old CSS changed only text colour. Streamlit could still
           render a white button in Night mode, making the text hard to
           read. We explicitly set both background and foreground.
           ========================================================== */
        [data-testid="stButton"] button,
        [data-testid="stDownloadButton"] button {{
            background: {th['surface']} !important;
            color: {th['text']} !important;
            border: 1px solid {th['border']} !important;
            border-radius: 10px !important;
        }}

        [data-testid="stButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover {{
            background: {th['border']} !important;
            color: {th['text']} !important;
        }}

        [data-testid="stButton"] button p,
        [data-testid="stDownloadButton"] button p,
        [data-testid="stButton"] button span,
        [data-testid="stDownloadButton"] button span {{
            color: {th['text']} !important;
        }}

        /* ==========================================================
           5. TEXT INPUTS, SELECTBOXES AND MULTISELECTS
           ========================================================== */
        input,
        textarea {{
            color: {th['text']} !important;
            background: {th['surface']} !important;
            border-color: {th['border']} !important;
        }}

        input::placeholder,
        textarea::placeholder {{
            color: {th['muted']} !important;
            opacity: 1 !important;
        }}

        [data-baseweb="select"] {{
            background: {th['surface']} !important;
            color: {th['text']} !important;
            border-color: {th['border']} !important;
        }}

        [data-baseweb="select"] > div {{
            background: {th['surface']} !important;
            color: {th['text']} !important;
            border-color: {th['border']} !important;
        }}

        [data-baseweb="select"] input,
        [data-baseweb="select"] [role="combobox"],
        [data-baseweb="select"] span {{
            color: {th['text']} !important;
        }}

        [data-baseweb="popover"],
        [data-baseweb="menu"],
        [role="listbox"],
        [role="option"] {{
            background: {th['surface']} !important;
            color: {th['text']} !important;
        }}

        [role="option"][aria-selected="true"] {{
            background: {th['border']} !important;
            color: {th['text']} !important;
        }}

        /* ==========================================================
           6. FILE UPLOADER
           This is one of Streamlit's more deeply nested widgets, so
           style the dropzone, instructions, buttons and file name.

           FIX: the block below (marked NEW) additionally targets the
           SVG icons Streamlit renders inside the uploader — the cloud
           upload icon and the small file/"remove" icons that appear
           after a file is added. Those are inline SVGs with their own
           fill colour, so the earlier rules (which only set `color`)
           never reached them — in Night/Midnight Blue they rendered as
           a near-black icon on a near-black background.
           ========================================================== */
        [data-testid="stFileUploader"] {{
            color: {th['text']} !important;
        }}

        [data-testid="stFileUploaderDropzone"] {{
            background: {th['surface']} !important;
            border: 1px dashed {th['border']} !important;
            color: {th['text']} !important;
        }}

        [data-testid="stFileUploaderDropzone"] * {{
            color: {th['text']} !important;
        }}

        [data-testid="stFileUploaderDropzoneInstructions"] {{
            color: {th['text']} !important;
        }}

        [data-testid="stFileUploaderDropzoneInstructions"] small {{
            color: {th['muted']} !important;
        }}

        [data-testid="stFileUploader"] button {{
            background: {th['surface']} !important;
            color: {th['text']} !important;
            border: 1px solid {th['border']} !important;
        }}

        /* NEW: cloud-upload icon and any other SVG glyph in the dropzone. */
        [data-testid="stFileUploaderDropzone"] svg {{
            fill: {th['muted']} !important;
            color: {th['muted']} !important;
        }}

        /* NEW: the row that appears for each uploaded file (name + size). */
        [data-testid="stFileUploaderFile"] {{
            background: {th['surface']} !important;
            color: {th['text']} !important;
        }}

        [data-testid="stFileUploaderFile"] * {{
            color: {th['text']} !important;
        }}

        /* NEW: the small document icon and the "x" remove icon on that row. */
        [data-testid="stFileUploaderFile"] svg,
        [data-testid="stFileUploaderDeleteBtn"] svg {{
            fill: {th['muted']} !important;
            color: {th['muted']} !important;
        }}

        /* ==========================================================
           7. DATAFRAMES / DATA INTELLIGENCE TABLES
           ========================================================== */
        [data-testid="stDataFrame"] {{
            background: {th['surface']} !important;
            border: 1px solid {th['border']} !important;
            border-radius: 10px !important;
            overflow: hidden !important;
        }}

        [data-testid="stDataFrame"] > div,
        [data-testid="stDataFrame"] [role="grid"] {{
            background: {th['surface']} !important;
            color: {th['text']} !important;
        }}

        /* ==========================================================
           8. EXPANDERS AND BORDERED CONTAINERS
           ========================================================== */
        [data-testid="stExpander"],
        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: {th['border']} !important;
        }}

        [data-testid="stExpander"] > details,
        [data-testid="stExpander"] summary {{
            background: {th['surface']} !important;
            color: {th['text']} !important;
        }}

        /* ==========================================================
           9. METRIC CARDS
           ========================================================== */
        [data-testid="stMetric"] {{
            background: {st.session_state.card_bg} !important;
            color: {th['text']} !important;
            border: 1px solid {th['border']} !important;
            border-radius: 14px;
            padding: 12px;
        }}

        [data-testid="stMetricValue"],
        [data-testid="stMetricLabel"],
        [data-testid="stMetricDelta"] {{
            color: {th['text']} !important;
        }}

        /* ==========================================================
           10. APPLICATION HERO
           ========================================================== */
        .hero {{
            padding: 22px 26px;
            border: 1px solid {th['border']};
            border-radius: 20px;
            background: {st.session_state.dashboard_bg};
            margin-bottom: 18px;
        }}

        .hero h1 {{
            margin: 0;
            font-size: 2.1rem;
            color: {th['text']} !important;
        }}

        .hero p {{
            margin: 5px 0 0;
            color: {th['muted']} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ---------- helpers ----------
def is_df_truthy(value):
    """Never evaluate a pandas DataFrame directly in an if statement."""
    if value is None:return False
    if isinstance(value,pd.DataFrame):return not value.empty
    if isinstance(value,(list,tuple,dict,set,str)):return bool(value)
    return bool(value)

def dataset_fingerprint(df): return (tuple(df.columns),len(df),tuple(map(str,df.dtypes)))

def init_dataset_state(df):
    fp=dataset_fingerprint(df)
    if st.session_state.get("data_fp")!=fp:
        st.session_state.data_fp=fp
        auto=automatic_chart_suggestions(df,minimum=8)
        st.session_state.dashboard_items=auto[:8]
        st.session_state.studio_items=[dict(x) for x in auto]
        st.session_state.kpi_items=build_kpi_catalog(df,st.session_state.analysis)
        st.session_state.dashboard_kpis=[]
        st.session_state.filters={}

def safe_kpis(result):
    k=result.get("kpis",[])
    return k if isinstance(k,list) else []

def build_kpi_catalog(df,result):
    items=[]
    for k in safe_kpis(result):
        if isinstance(k,dict) and k.get("name"):
            items.append({**k,"formula":k.get("formula",f"SUM({k.get('source','')})")})
    nums=numeric_columns(df)
    existing={x.get("name") for x in items}
    fallbacks=[("Total Rows",len(df),"COUNT_ROWS"),("Numeric Fields",len(nums),"COUNT_NUMERIC_FIELDS")]
    for name,val,formula in fallbacks:
        if name not in existing: items.append({"name":name,"value":val,"display_value":f"{val:,}","formula":formula,"format":"number"})
    return items[:12]

def formula_value(df,formula):
    f=str(formula).strip()
    if f.upper()=="COUNT_ROWS":return float(len(df))
    if f.upper()=="COUNT_NUMERIC_FIELDS":return float(len(numeric_columns(df)))
    def col(name):
        name=name.strip().strip("[]\"")
        if name not in df.columns: raise ValueError(f"Column not found: {name}")
        return to_numeric_series(df[name])
    m=f.upper()
    # Basic safe formula language: SUM, AVG, MIN, MAX, MEDIAN, COUNT, UNIQUE and + - * /.
    for fn,op in [("SUM","sum"),("AVG","mean"),("AVERAGE","mean"),("MIN","min"),("MAX","max"),("MEDIAN","median")]:
        import re
        pattern=rf"{fn}\(([^()]+)\)"
        while re.search(pattern,f,re.I):
            match=re.search(pattern,f,re.I); c=match.group(1).strip(); s=col(c); val=getattr(s,op)()
            f=f[:match.start()]+str(float(val))+f[match.end():]
    import re
    f=re.sub(r"COUNT\(([^()]+)\)",lambda m:str(float(col(m.group(1)).notna().sum())),f,flags=re.I)
    f=re.sub(r"UNIQUE\(([^()]+)\)",lambda m:str(float(df[m.group(1).strip()].nunique(dropna=True))),f,flags=re.I)
    if not re.fullmatch(r"[0-9eE+\-*/(). %]+",f): raise ValueError("Formula contains unsupported text. Use SUM(Column), AVG(Column), MIN(Column), MAX(Column), MEDIAN(Column), COUNT(Column), UNIQUE(Column), and + - * /.")
    return float(eval(f,{"__builtins__":{}},{}))

def display_kpi(item,df):
    try:
        if item.get("formula"): value=formula_value(df,item["formula"])
        else:value=float(item.get("value",0))
    except Exception:value=item.get("value","—")
    fmt=item.get("format","number")
    if fmt=="currency":return format_currency(value,st.session_state.currency)
    if fmt=="percent":return f"{value:,.2f}%"
    if isinstance(value,(int,float,np.number)):return f"{float(value):,.2f}" if float(value)%1 else f"{int(value):,}"
    return str(value)

def global_filter_ui(df,prefix="global"):
    # Slicers are dimensions/categories only, never numeric measures.
    numeric=set(numeric_columns(df))
    cats=[c for c in df.columns if c not in numeric and df[c].nunique(dropna=True)<=80 and df[c].nunique(dropna=True)>1]
    if not cats:return {}
    selected={}
    st.markdown("#### Slicers")
    cols=st.columns(min(4,max(1,len(cats[:4]))))
    for i,c in enumerate(cats[:4]):
        vals=sorted(df[c].dropna().astype(str).unique().tolist())
        with cols[i%len(cols)]:
            choice=st.multiselect(c,vals,key=f"{prefix}_{i}")
            if choice:selected[c]=choice
    return selected

def toggle_state(name):
    st.session_state[name] = not st.session_state.get(name, True)

def sync_pref(name, widget_key):
    st.session_state[name] = st.session_state[widget_key]

# ---------- sidebar ----------
with st.sidebar:
    st.markdown("## 📊 CSV Auto-Analyzer")
    cur_names=list(CURRENCIES)
    st.selectbox("Currency",cur_names,index=cur_names.index(st.session_state.currency),key="sidebar_currency",on_change=sync_pref,args=("currency","sidebar_currency"))
    st.selectbox(
        "Theme",
        list(THEMES),
        index=list(THEMES).index(st.session_state.theme),
        key="sidebar_theme",
        on_change=sync_theme_from_widget,
    )
    uploaded=st.file_uploader("Upload CSV",type=["csv"],help="CSV files are analyzed in the current session.")
    st.divider()
    page=st.radio("Workspace",["Dashboard","Chart Studio","KPI Studio","Forecast","Data Intelligence","Reports","Saved Dashboards","Settings"],index=0)

# Re-apply after controls so a theme change is reflected immediately.
apply_theme()

if uploaded is not None and uploaded.name!=st.session_state.filename:
    try:
        df=pd.read_csv(uploaded)
        if df.empty:st.error("This CSV contains no rows.");st.stop()
        st.session_state.df=df;st.session_state.filename=uploaded.name;st.session_state.analysis=analyze(df);init_dataset_state(df)
    except Exception as exc:st.error(f"Could not read this CSV: {exc}");st.stop()

df=st.session_state.df; result=st.session_state.analysis
st.markdown('<div class="hero"><h1>📊 CSV Auto-Analyzer</h1><p>Business intelligence, interactive dashboards, forecasting and explainable data answers — built for e-commerce and general business data.</p></div>',unsafe_allow_html=True)
if df is None:
    st.info("Upload a CSV to begin. After deployment, end users only need the website — they do not need Python or VS Code.")
    st.stop()
init_dataset_state(df)
platform,amazon_score,walmart_score=detect_ecommerce_platform(df.columns)

# ---------- dashboard ----------
if page=="Dashboard":
    st.subheader("Executive Dashboard")
    st.caption(f"{st.session_state.filename} · detected: **{platform}**")
    global_filters=global_filter_ui(df,"dash_filter")
    items=st.session_state.dashboard_items or automatic_chart_suggestions(df,8)
    # Controls
    c1,c2,c3,c4=st.columns(4)
    with c1:
        if st.button("➕ Add chart",key="dash_add_chart"): items.append({"id":f"user_{len(items)}","type":"Bar Chart","title":"New Chart","x":None,"y":None,"color":"Professional"});st.session_state.dashboard_items=items;st.rerun()
    with c2:
        st.button("📐 Dashboard settings",key="dash_settings_btn",on_click=toggle_state,args=("dash_settings",))
    with c3:
        if st.button("↩ Reset",key="dash_reset"): st.session_state.dashboard_items=automatic_chart_suggestions(df,8);st.rerun()
    with c4:
        if st.button("💾 Save dashboard",key="dash_save"): st.session_state.save_dash_open=True
    if st.session_state.get("save_dash_open"):
        name=st.text_input("Dashboard name",value=Path(st.session_state.filename).stem,key="save_dash_name")
        if st.button("Confirm save",key="confirm_save"):
            did=save_dashboard(name,st.session_state.filename,{"items":items,"kpis":st.session_state.kpi_items,"theme":st.session_state.theme,"currency":st.session_state.currency});st.success(f"Saved dashboard #{did}");st.session_state.save_dash_open=False
    if st.session_state.get("dash_settings",True):
        a,b,c=st.columns(3)
        with a: st.session_state.dashboard_bg=st.color_picker("Dashboard background",st.session_state.dashboard_bg,key="dash_bg")
        with b: st.session_state.card_bg=st.color_picker("Card background",st.session_state.card_bg,key="dash_card_bg")
        with c: st.session_state.chart_bg=st.color_picker("Chart background",st.session_state.chart_bg,key="dash_chart_bg")
    kpis=st.session_state.get("dashboard_kpis") or st.session_state.kpi_items or build_kpi_catalog(df,result)
    kc=st.columns(min(4,max(1,len(kpis[:4]))))
    for i,k in enumerate(kpis[:4]):
        with kc[i]:
            kb=k.get("background",st.session_state.card_bg)
            st.markdown(
                f"""
                <div class="dashboard-kpi" style="
                    background:{kb};
                    color:{THEMES[st.session_state.theme]['text']};
                    border:1px solid {THEMES[st.session_state.theme]['border']};
                    border-radius:14px;
                    padding:15px 17px;
                    min-height:105px;
                "">
                    <div style="font-size:.84rem;color:inherit;opacity:.78">
                        {k.get('name', f'KPI {i+1}')}
                    </div>
                    <div style="font-size:1.65rem;font-weight:700;margin-top:7px;color:inherit">
                        {display_kpi(k, df)}
                    </div>
                    <div style="font-size:.72rem;margin-top:5px;color:inherit;opacity:.62">
                        {k.get('formula', '')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown(f"**Dashboard visuals:** {len(items)} · minimum automatic layout: 8 charts")
    n=len(items); cols_per_row=4 if n>=12 else 3 if n>=9 else 2
    for start in range(0,n,cols_per_row):
        row=items[start:start+cols_per_row]; cc=st.columns(cols_per_row)
        for pos,item in enumerate(row):
            with cc[pos]:
                with st.container(border=True):
                    fig=build_chart(df,item,global_filters)
                    if fig is not None:st.plotly_chart(fig,use_container_width=True,key=f"db_fig_{start}_{pos}_{item.get('id','x')}")
                    elif item.get("type")=="Table":st.dataframe(prepare_chart_data(df,item,global_filters).head(50),use_container_width=True,hide_index=True)
                    else:st.warning("Configure this visual in Chart Studio.")
                    x,y=st.columns(2)
                    if x.button("✏️ Edit",key=f"db_edit_{start}_{pos}"):st.session_state.edit_chart_index=start+pos;st.session_state.goto_studio=True
                    if y.button("🗑 Remove",key=f"db_remove_{start}_{pos}"):st.session_state.dashboard_items.pop(start+pos);st.rerun()

# ---------- chart studio ----------
elif page=="Chart Studio":
    st.subheader("📈 Chart Studio")
    st.caption("Build business visuals with slicers, ranking, filtering, palette and custom background controls.")
    items=st.session_state.studio_items or automatic_chart_suggestions(df,8)
    a,b,c=st.columns(3)
    with a:
        if st.button("➕ Add chart",key="studio_add"):items.append({"id":f"studio_{len(items)}","type":"Bar Chart","title":"New Chart","x":None,"y":None,"color":"Professional"});st.session_state.studio_items=items;st.rerun()
    with b:
        if st.button("⚙️ Hide chart settings",key="studio_hide"):st.session_state.chart_settings=not st.session_state.get("chart_settings",True)
    with c:
        if st.button("➕ Add all charts to dashboard",key="studio_all"):st.session_state.dashboard_items=[dict(x) for x in items];st.success(f"{len(items)} charts are on the dashboard.")
    if st.button("↩ Reset studio",key="studio_reset"):
        st.session_state.studio_items=[dict(x) for x in automatic_chart_suggestions(df,8)];st.rerun()
    show_settings=st.session_state.get("chart_settings",True)
    nums=numeric_columns(df); cols=list(df.columns)
    for i,item in enumerate(items):
        with st.container(border=True):
            st.markdown(f"### Chart {i+1}")
            if show_settings:
                a,b,c=st.columns(3)
                with a:item["title"]=st.text_input("Title",item.get("title","Chart"),key=f"ctitle_{i}")
                with b:item["type"]=st.selectbox("Chart type",CHART_TYPES,index=CHART_TYPES.index(item.get("type")) if item.get("type") in CHART_TYPES else 0,key=f"ctype_{i}")
                with c:item["color"]=st.selectbox("Colour theme",list(CHART_PALETTES),index=list(CHART_PALETTES).index(item.get("color","Professional")) if item.get("color") in CHART_PALETTES else 0,key=f"ccolor_{i}")
                a,b,c=st.columns(3)
                with a:item["x"]=st.selectbox("X / Category",["None"]+cols,index=(["None"]+cols).index(item.get("x")) if item.get("x") in cols else 0,key=f"cx_{i}")
                with b:item["y"]=st.selectbox("Y / Value",["None"]+nums,index=(["None"]+nums).index(item.get("y")) if item.get("y") in nums else 0,key=f"cy_{i}")
                with c:item["background"]=st.color_picker("Custom chart background",item.get("background",st.session_state.chart_bg),key=f"cbg_{i}")
                a,b,c=st.columns(3)
                with a:
                    fc=st.selectbox("Filter column",["None"]+cols,index=(["None"]+cols).index(item.get("filter_column")) if item.get("filter_column") in cols else 0,key=f"cfc_{i}");item["filter_column"]=None if fc=="None" else fc
                with b:
                    if item.get("filter_column"):
                        vals=sorted(df[item["filter_column"]].dropna().astype(str).unique().tolist()[:500]);item["filter_value"]=st.selectbox("Filter value",["All"]+vals,key=f"cfv_{i}")
                    else:item["filter_value"]=None
                with c:
                    item["ranking"]=st.selectbox("Ranking",["None","Top N","Bottom N"],index=["None","Top N","Bottom N"].index(item.get("ranking","None")),key=f"crank_{i}")
                    if item["ranking"]!="None":item["n"]=st.number_input("N",1,100,int(item.get("n",10)),key=f"cn_{i}")
            fig=build_chart(df,item,st.session_state.get("filters",{}))
            if fig is not None:st.plotly_chart(fig,use_container_width=True,key=f"studio_plot_{i}_{item.get('id')}")
            else:st.info("Choose the required X/Y fields for this visual.")
            a,b,c=st.columns(3)
            with a:
                if st.button("➕ Add to Dashboard",key=f"add_db_{i}"):
                    if not any(x.get("id")==item.get("id") for x in st.session_state.dashboard_items):st.session_state.dashboard_items.append(dict(item))
                    st.success("Chart added to dashboard.")
            with b:
                if st.button("🗑 Delete",key=f"del_chart_{i}"):st.session_state.studio_items.pop(i);st.rerun()
            with c:
                if st.button("📊 Compare",key=f"cmp_{i}"):st.session_state.compare_chart=item
    if st.session_state.get("compare_chart"):
        st.subheader("Chart comparison")
        selected=items[:4]
        cc=st.columns(min(4,len(selected)))
        for i,it in enumerate(selected):
            with cc[i]:
                fig=build_chart(df,it)
                if fig:st.plotly_chart(fig,use_container_width=True,key=f"compare_view_{i}")

# ---------- KPI studio ----------
elif page=="KPI Studio":
    st.subheader("📌 KPI Studio")
    st.caption("Create formula-driven KPI cards. Every KPI can be placed on the dashboard.")
    items=st.session_state.kpi_items
    a,b,c=st.columns(3)
    with a:
        # FIX: new KPIs now default to the current theme's card colour
        # instead of a hardcoded white, so a KPI created in Night theme
        # is dark from the start.
        if st.button("➕ Add KPI",key="kpi_add"):items.append({"name":"New KPI","formula":"SUM( )","format":"number","background":st.session_state.card_bg});st.rerun()
    with b:
        if st.button("⚙️ Hide KPI settings",key="kpi_hide"):st.session_state.kpi_settings=not st.session_state.get("kpi_settings",True)
    with c:
        if st.button("➕ Add all KPIs to dashboard",key="kpi_all"):st.session_state.dashboard_kpis=items;st.success("KPIs are available for the dashboard.")
    if st.session_state.get("kpi_settings",True):
        st.info("Formula examples: `SUM(Ordered Product Sales)`, `AVG(Units Ordered)`, `SUM(Sales) / SUM(Units)`, `UNIQUE(Customer ID)`.")

    # ============================================================
    # NEW: "same colour for all KPIs" control.
    # When switched on, one shared colour picker drives every KPI
    # card's background at once instead of colouring each one by hand.
    # ============================================================
    uniform_col, picker_col = st.columns([1, 2])
    with uniform_col:
        uniform = st.checkbox(
            "🎨 Use one colour for all KPIs",
            value=st.session_state.get("kpi_uniform_color", False),
            key="kpi_uniform_color",
            help="Turn this on to colour every KPI card the same way, instead of picking a colour for each one individually.",
        )
    with picker_col:
        if uniform:
            default_shared = st.session_state.get("kpi_shared_bg") or st.session_state.card_bg
            shared_bg = st.color_picker(
                "Shared KPI background",
                default_shared,
                key="kpi_shared_bg",
            )
            # Apply the shared colour to every KPI immediately so the
            # Dashboard page picks it up as soon as it is set.
            for k in items:
                k["background"] = shared_bg

    for i,k in enumerate(items):
        with st.container(border=True):
            a,b,c,d=st.columns(4)
            with a:k["name"]=st.text_input("KPI name",k.get("name",f"KPI {i+1}"),key=f"kn_{i}")
            with b:k["formula"]=st.text_input("Custom formula",k.get("formula",""),key=f"kf_{i}")
            with c:k["format"]=st.selectbox("Format",["number","currency","percent"],index=( ["number","currency","percent"].index(k.get("format")) if k.get("format") in ["number","currency","percent"] else 0 ),key=f"kfmt_{i}")
            with d:
                if uniform:
                    # Colour is driven by the shared picker above — show the
                    # current colour here for reference only, disabled so it
                    # can't drift out of sync with the shared setting.
                    st.color_picker("KPI background",k.get("background",st.session_state.card_bg),key=f"kbg_{i}",disabled=True)
                else:
                    # FIX: default is now the current theme's card colour
                    # (was hardcoded "#FFFFFF"), so an untouched KPI follows
                    # the active theme instead of always starting white.
                    k["background"]=st.color_picker("KPI background",k.get("background",st.session_state.card_bg),key=f"kbg_{i}")
            st.metric(k["name"],display_kpi(k,df))
            a,b=st.columns(2)
            if a.button("➕ Add to Dashboard",key=f"kadd_{i}"):st.session_state.dashboard_kpis=st.session_state.get("dashboard_kpis",[])+[dict(k)];st.success("KPI added to dashboard.")
            if b.button("🗑 Delete",key=f"kdel_{i}"):items.pop(i);st.rerun()

# ---------- forecast ----------
elif page=="Forecast":
    st.subheader("🔮 Forecast & Future Insights")
    st.caption("Designed for planning: select a time series, choose the future horizon and let Auto select the method using holdout validation.")
    dates=result.get("dates",[]); nums=numeric_columns(df)
    if not dates or not nums:st.warning("Forecasting needs a usable date column and numeric measure.")
    else:
        a,b,c=st.columns(3)
        with a:dcol=st.selectbox("Time column",dates,key="fc_date")
        with b:vcol=st.selectbox("Measure",nums,key="fc_value")
        with c:freq=st.selectbox("Forecast frequency",["D","W","MS","QS","YS"],index=2,key="fc_freq")
        a,b=st.columns(2)
        with a:periods=st.number_input("Future periods",1,36,6,key="fc_periods")
        with b:method=st.selectbox("Model",["Auto","Naive","Moving average","Linear trend","Exponential trend"],key="fc_method")
        if st.button("🚀 Generate forecast",type="primary",key="fc_run"):
            try:
                fc=forecast_series(df,dcol,vcol,int(periods),freq,method)
                hist=fc["history"]; pred=fc["forecast"]
                fig=go.Figure()
                fig.add_trace(go.Scatter(x=hist.date,y=hist.value,name="Historical",mode="lines+markers"))
                # Connector makes the boundary explicit rather than leaving a confusing gap.
                fig.add_trace(go.Scatter(x=[hist.date.iloc[-1],pred.date.iloc[0]],y=[hist.value.iloc[-1],pred.prediction.iloc[0]],name="Transition",mode="lines",line=dict(dash="dot"),showlegend=False))
                fig.add_trace(go.Scatter(x=pred.date,y=pred.prediction,name=f"Forecast ({int(periods)} periods)",mode="lines+markers"))
                fig.add_trace(go.Scatter(x=list(pred.date)+list(pred.date[::-1]),y=list(pred.upper)+list(pred.lower[::-1]),fill="toself",fillcolor="rgba(100,149,237,.12)",line=dict(color="rgba(0,0,0,0)"),name="Uncertainty band"))
                fig.update_layout(height=500,title=f"{vcol}: {len(hist)} historical periods + {int(periods)} forecast periods",hovermode="x unified",margin=dict(l=25,r=25,t=65,b=30))
                st.plotly_chart(fig,use_container_width=True)
                d=fc["diagnostics"]
                a,b,c,dcol2=st.columns(4);a.metric("Forecast periods",d["forecast_periods"]);b.metric("Model",d["method"]);c.metric("Validation RMSE",f"{d['rmse']:,.2f}");dcol2.metric("Trend",d["trend"].title())
                st.write("**Method comparison (holdout):**")
                scores=d.get("model_scores",{});st.dataframe(pd.DataFrame(scores).T.reset_index().rename(columns={"index":"Model"}),use_container_width=True,hide_index=True)
                st.write("**Future values:**");st.dataframe(pred,use_container_width=True,hide_index=True)
                st.info(d["warning"])
            except Exception as exc:st.error(str(exc))

# ---------- intelligence ----------
elif page=="Data Intelligence":
    st.subheader("🧠 Data Intelligence")
    st.caption("This page explains what the data means, what is reliable, what needs attention and what you can ask about it.")
    a,b,c,d=st.columns(4);a.metric("Rows",f"{len(df):,}");b.metric("Columns",f"{len(df.columns):,}");c.metric("Numeric",len(numeric_columns(df)));d.metric("Health",f"{result['quality'].get('health_score','—')}/100")
    st.markdown(f"### Detected business context: **{platform}**")
    st.write(f"Amazon signal: **{amazon_score}** · Walmart signal: **{walmart_score}**")
    # High-value profile instead of exposing only raw internal objects.
    date_cols=result.get("dates",[])
    num_cols=numeric_columns(df)
    missing=df.isna().sum().sort_values(ascending=False)
    profile_cols=st.columns(4)
    profile_cols[0].metric("Measures",len(num_cols))
    profile_cols[1].metric("Dimensions",len(df.columns)-len(num_cols)-len(date_cols))
    profile_cols[2].metric("Missing cells",f"{int(missing.sum()):,}")
    if date_cols:
        parsed=pd.to_datetime(df[date_cols[0]],errors="coerce").dropna()
        profile_cols[3].metric("Time span",f"{parsed.min().date()} → {parsed.max().date()}" if not parsed.empty else "—")
    else:
        profile_cols[3].metric("Time fields",0)
    if num_cols:
        st.markdown("**Most useful measures**")
        measure_rows=[]
        for col in num_cols[:12]:
            ss=to_numeric_series(df[col])
            measure_rows.append({"Measure":col,"Total":round(float(ss.sum()),2),"Average":round(float(ss.mean()),2),"Min":round(float(ss.min()),2),"Max":round(float(ss.max()),2)})
        st.dataframe(pd.DataFrame(measure_rows),use_container_width=True,hide_index=True)
    if missing.iloc[0] > 0:
        st.warning(f"Data quality priority: **{missing.index[0]}** has {int(missing.iloc[0]):,} missing cells.")
    st.subheader("Column intelligence")
    st.dataframe(result.get("business",pd.DataFrame()),use_container_width=True,hide_index=True)
    st.subheader("What stands out")
    for insight in result.get("insights",[]):st.write("• "+str(insight))
    corr=result.get("correlations")
    if isinstance(corr,pd.DataFrame) and not corr.empty:
        st.subheader("Strong relationships");st.dataframe(corr.head(15),use_container_width=True,hide_index=True)
    else:st.info("No strong numeric relationships crossed the configured threshold.")
    st.subheader("Ask questions about this dataset")
    q=st.text_input("Ask in plain English",placeholder="What is the average Units Ordered? Which column has the most missing values?",key="data_question")
    if q:
        st.success(answer_question(df,q))

# ---------- reports ----------
elif page=="Reports":
    st.subheader("📄 Reports & exports")
    a,b=st.columns(2)
    with a:
        if st.button("Generate PDF",type="primary",key="make_pdf"):
            data=pdf_report(st.session_state.filename,df,safe_kpis(result)[:4],result.get("insights",[]),result.get("quality",{}));st.download_button("Download PDF",data,file_name=f"{Path(st.session_state.filename).stem}_report.pdf",mime="application/pdf",key="dl_pdf")
    with b:
        if st.button("Generate Excel",type="primary",key="make_xlsx"):
            data=excel_report(df,result.get("business",pd.DataFrame()),safe_kpis(result)[:4],result.get("insights",[]),result.get("quality",{}),filename=st.session_state.filename);st.download_button("Download Excel",data,file_name=f"{Path(st.session_state.filename).stem}_report.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",key="dl_xlsx")

# ---------- saved ----------
elif page=="Saved Dashboards":
    st.subheader("💾 Saved Dashboards")
    items=list_dashboards()
    if not items:st.info("No saved dashboards yet. Save one from the Dashboard page.")
    for item in items:
        with st.container(border=True):
            a,b,c=st.columns([6,2,1]);a.markdown(f"**{item['name']}** · {item['source_file'] or 'No source'}");b.caption(item['updated_at'][:19].replace("T"," "))
            if c.button("Delete",key=f"saved_del_{item['id']}"):delete_dashboard(item["id"]);st.rerun()
            if st.button("Open dashboard",key=f"saved_open_{item['id']}"):
                payload=load_dashboard(item["id"]);st.session_state.dashboard_items=payload["payload"].get("items",[]);st.session_state.studio_items=[dict(x) for x in st.session_state.dashboard_items];st.session_state.kpi_items=payload["payload"].get("kpis",st.session_state.kpi_items);st.session_state.dashboard_kpis=st.session_state.kpi_items;st.success(f"Loaded {item['name']}. Go to Dashboard to view it.")

# ---------- settings ----------
else:
    st.subheader("⚙️ Settings")
    st.write("These are live application controls, not documentation.")
    a,b=st.columns(2)
    with a:
        st.selectbox(
            "Interface theme",
            list(THEMES),
            index=list(THEMES).index(st.session_state.theme),
            key="settings_theme",
            on_change=sync_theme_from_settings,
        )
        cur=list(CURRENCIES);st.selectbox("Display currency",cur,index=cur.index(st.session_state.currency),key="settings_currency",on_change=sync_pref,args=("currency","settings_currency"))
    with b:
        st.session_state.dashboard_bg=st.color_picker("Default dashboard background",st.session_state.dashboard_bg,key="settings_dashbg")
        st.session_state.card_bg=st.color_picker("Default KPI/card background",st.session_state.card_bg,key="settings_cardbg")
        st.session_state.chart_bg=st.color_picker("Default chart background",st.session_state.chart_bg,key="settings_chartbg")
    st.subheader("Data processing")
    st.checkbox("Treat numeric-looking text as numeric",True,key="setting_numeric")
    st.checkbox("Show uncertainty bands on forecasts",True,key="setting_uncertainty")
    st.checkbox("Enable automatic dashboard generation",True,key="setting_auto_dashboard")
    st.subheader("Deployment")
    st.success("This project is deployable as a web app. End users do not need Python or VS Code once the repository is deployed to a hosting service.")