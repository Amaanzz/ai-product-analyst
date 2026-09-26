
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))



import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from metrics.funnel import compute_funnel
from metrics.retention import (
    compute_retention_curve,
    compute_behavioural_cohort_comparison,
)
from metrics.kpi import compute_kpi_summary
from ai_analysis.ai_feature_metrics import compute_adoption, compute_quality, compute_cost
from business_impact.roi import compute_business_impact
from experimentation.ab_test import two_proportion_z_test, interpret
from segmentation.segment_users import (
    build_segmentation_features,
    rule_based_segments,
    kmeans_segments,
    profile_clusters,
    suggest_cluster_action,
    compare_segmentations,
)
from experimentation.segment_experiment import (
    segmented_ab_results,
    summarize_heterogeneity,
)
from recommendations.engine import generate_recommendations
from recommendations.rice_scoring import build_initiative_table


# ============================================================
# INSIGHTAI // PREMIUM PRODUCT INTELLIGENCE DASHBOARD
# ============================================================

st.set_page_config(
    page_title="InsightAI | Product Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Premium visual system
# -----------------------------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
    --black: #050607;
    --black-2: #090b0d;
    --panel: #0d1013;
    --panel-2: #111519;
    --panel-3: #151a1e;
    --silver: #d7d9dc;
    --silver-2: #a7adb3;
    --muted: #70777f;
    --line: rgba(210, 215, 220, .12);
    --line-strong: rgba(210, 215, 220, .22);
    --white: #f4f5f6;
    --green: #78d6a3;
    --amber: #e7c57a;
    --red: #e78282;
    --blue: #91b7d8;
}


[data-baseweb="tag"] {
    background: linear-gradient(145deg, #24292d, #111417) !important;
    border: 1px solid rgba(215,217,220,.22) !important;
    border-radius: 999px !important;
    color: #d7d9dc !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.06) !important;
}

[data-baseweb="tag"] span {
    color: #d7d9dc !important;
}

[data-baseweb="tag"] svg {
    fill: #aeb4b9 !important;
    color: #aeb4b9 !important;
}


/* Final device-filter treatment */
[data-testid="stMultiSelect"] [data-baseweb="tag"],
[data-testid="stMultiSelect"] [data-baseweb="tag"] > span {
    background: #171a1d !important;
    background-image: linear-gradient(145deg, #25292d 0%, #121416 100%) !important;
    border: 1px solid rgba(215,217,220,.24) !important;
    border-radius: 999px !important;
    color: #d7d9dc !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.07), 0 2px 8px rgba(0,0,0,.25) !important;
}

[data-testid="stMultiSelect"] [data-baseweb="tag"] span {
    color: #d7d9dc !important;
}

[data-testid="stMultiSelect"] [data-baseweb="tag"] svg {
    fill: #aeb4b9 !important;
    color: #aeb4b9 !important;
}


.ai-feature-head > div:first-child {
    flex: 0 0 auto;
    min-width: 360px;
}

.ai-feature-head .section-desc {
    flex: 1 1 auto;
    max-width: 760px;
}

@media (max-width: 1050px) {
    .ai-feature-head > div:first-child {
        min-width: 0;
    }
}

html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 82% 0%, rgba(192,198,204,.07), transparent 28%),
        radial-gradient(circle at 10% 35%, rgba(130,138,146,.035), transparent 30%),
        #050607 !important;
    color: var(--white) !important;
    font-family: Inter, sans-serif !important;
}

[data-testid="stAppViewContainer"] > .main {
    background: transparent !important;
}

[data-testid="stHeader"] {
    background: rgba(5,6,7,.82) !important;
    backdrop-filter: blur(18px);
}

.block-container {
    max-width: 1500px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
}

[data-testid="stSidebar"] {
    background:
        linear-gradient(180deg, #090b0d 0%, #060708 100%) !important;
    border-right: 1px solid var(--line) !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.2rem;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] label {
    color: var(--silver-2) !important;
}

[data-testid="stSidebar"] .stRadio label {
    border-radius: 10px;
    padding: .35rem .5rem;
    transition: .2s ease;
}

[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(255,255,255,.055);
    color: var(--white) !important;
}

[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 3px !important;
}

h1, h2, h3, h4 {
    font-family: "Space Grotesk", Inter, sans-serif !important;
    letter-spacing: -.035em !important;
    color: var(--white) !important;
}

h1 {
    font-size: 2.35rem !important;
    margin-bottom: .15rem !important;
}

h2 { font-size: 1.45rem !important; }
h3 { font-size: 1.05rem !important; }

p, li, span, label {
    color: var(--silver-2);
}

[data-testid="stMetric"] {
    position: relative;
    overflow: hidden;
    background:
        linear-gradient(145deg, rgba(255,255,255,.075), rgba(255,255,255,.018) 42%, rgba(0,0,0,.22)),
        var(--panel);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 1rem 1.1rem !important;
    min-height: 118px;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.07),
        0 18px 45px rgba(0,0,0,.22);
}

[data-testid="stMetric"]:before {
    content: "";
    position: absolute;
    top: 0;
    left: 12%;
    right: 12%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(230,233,236,.6), transparent);
}

[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
    font-size: .72rem !important;
    text-transform: uppercase;
    letter-spacing: .12em;
}

[data-testid="stMetricValue"] {
    color: var(--white) !important;
    font-family: "Space Grotesk", Inter, sans-serif !important;
    font-size: 1.9rem !important;
}

[data-testid="stMetricDelta"] {
    color: var(--silver-2) !important;
}

.stButton button, .stDownloadButton button {
    border: 1px solid var(--line-strong) !important;
    background: linear-gradient(145deg, #1a1f23, #0b0e10) !important;
    color: var(--silver) !important;
    border-radius: 10px !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.08), 0 8px 20px rgba(0,0,0,.2);
}

.stButton button:hover {
    border-color: rgba(235,238,240,.45) !important;
    color: white !important;
    transform: translateY(-1px);
}

[data-baseweb="select"] > div,
[data-baseweb="input"] > div {
    background: #0d1013 !important;
    border-color: var(--line-strong) !important;
    color: var(--silver) !important;
    border-radius: 10px !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
    overflow: hidden !important;
}

[data-testid="stExpander"] {
    background: rgba(255,255,255,.025);
    border: 1px solid var(--line) !important;
    border-radius: 14px !important;
}

hr {
    border-color: var(--line) !important;
}

[data-testid="stCaptionContainer"] {
    color: var(--muted) !important;
}

.insight-shell {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 18px 22px;
    margin-bottom: 20px;
    border: 1px solid var(--line-strong);
    border-radius: 18px;
    background:
        linear-gradient(120deg, rgba(255,255,255,.075), rgba(255,255,255,.018) 46%, rgba(0,0,0,.22)),
        rgba(10,12,14,.88);
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.08),
        0 22px 55px rgba(0,0,0,.25);
}

.brand {
    display:flex;
    align-items:center;
    gap:12px;
}

.brand-mark {
    width:42px;
    height:42px;
    border-radius:12px;
    display:grid;
    place-items:center;
    color:#080909;
    font-weight:800;
    font-size:20px;
    background:
        linear-gradient(145deg,#f1f2f3 0%,#a9adb1 48%,#6e7378 100%);
    box-shadow:
        inset 1px 1px 1px rgba(255,255,255,.75),
        inset -2px -2px 4px rgba(0,0,0,.3),
        0 8px 20px rgba(0,0,0,.35);
}

.brand-title {
    font-family:"Space Grotesk",Inter,sans-serif;
    color:var(--white);
    font-size:1.05rem;
    font-weight:700;
    letter-spacing:-.02em;
}

.brand-sub {
    color:var(--muted);
    font-size:.72rem;
    margin-top:2px;
}

.status-pill {
    display:flex;
    align-items:center;
    gap:7px;
    padding:7px 11px;
    border:1px solid var(--line);
    border-radius:999px;
    color:var(--silver-2);
    font-size:.72rem;
    background:rgba(255,255,255,.025);
}

.status-dot {
    width:7px;
    height:7px;
    border-radius:50%;
    background:var(--green);
    box-shadow:0 0 12px rgba(120,214,163,.45);
}

.section-head {
    display:flex;
    align-items:end;
    justify-content:space-between;
    gap:24px;
    min-width:0;
    margin: 6px 0 18px;
}

.eyebrow {
    color:#858c93;
    font-size:.67rem;
    font-weight:700;
    text-transform:uppercase;
    letter-spacing:.16em;
    margin-bottom:5px;
}

.section-title {
    color:#f2f3f4;
    font-family:"Space Grotesk",Inter,sans-serif;
    font-size:1.65rem;
    font-weight:700;
    letter-spacing:-.04em;
}

.section-desc {
    color:#70777f;
    font-size:.82rem;
    max-width:680px;
    min-width:0;
    line-height:1.5;
}

.section-head > div:first-child {
    min-width:0;
}

@media (max-width: 1050px) {
    .section-head {
        align-items:flex-start;
        flex-direction:column;
        gap:7px;
    }
    .section-desc {
        max-width:760px;
    }
}

.glass-card {
    padding:18px;
    border:1px solid var(--line);
    border-radius:16px;
    background:
        linear-gradient(145deg, rgba(255,255,255,.055), rgba(255,255,255,.012) 55%, rgba(0,0,0,.18)),
        #0b0e10;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.045),
        0 18px 45px rgba(0,0,0,.2);
}

.hero-card {
    padding:22px 24px;
    border-radius:20px;
    border:1px solid rgba(210,215,220,.17);
    background:
        radial-gradient(circle at 82% 25%, rgba(220,224,228,.10), transparent 25%),
        linear-gradient(135deg, rgba(255,255,255,.075), rgba(255,255,255,.018) 50%, rgba(0,0,0,.28)),
        #0a0c0e;
    box-shadow:
        inset 0 1px 0 rgba(255,255,255,.09),
        inset 0 -1px 0 rgba(0,0,0,.7),
        0 28px 65px rgba(0,0,0,.28);
}

.hero-kicker {
    color:#7f878e;
    font-size:.7rem;
    text-transform:uppercase;
    letter-spacing:.15em;
    font-weight:700;
}

.hero-value {
    font-family:"Space Grotesk",Inter,sans-serif;
    font-size:2.5rem;
    font-weight:700;
    color:#f5f6f7;
    letter-spacing:-.06em;
    margin:4px 0;
}

.hero-note {
    color:#7f878e;
    font-size:.78rem;
}

.badge {
    display:inline-flex;
    align-items:center;
    gap:6px;
    padding:5px 9px;
    border-radius:999px;
    border:1px solid var(--line);
    background:rgba(255,255,255,.03);
    color:#b9bec3;
    font-size:.68rem;
    text-transform:uppercase;
    letter-spacing:.09em;
}

.badge-green { color:#91dfb5; border-color:rgba(120,214,163,.2); }
.badge-amber { color:#e7c57a; border-color:rgba(231,197,122,.2); }

.sidebar-note {
    padding:12px 13px;
    border:1px solid var(--line);
    border-radius:12px;
    background:rgba(255,255,255,.025);
    font-size:.72rem;
    line-height:1.5;
    color:#777e85;
}

[data-testid="stPlotlyChart"] {
    border:1px solid var(--line);
    border-radius:16px;
    overflow:hidden;
    background:#0a0c0e;
    box-shadow:0 18px 45px rgba(0,0,0,.18);
}

[data-testid="stPlotlyChart"] > div {
    border-radius:16px;
}

.small-label {
    color:#747b82;
    text-transform:uppercase;
    letter-spacing:.12em;
    font-size:.65rem;
    font-weight:700;
}

@media (max-width: 800px) {
    .block-container { padding-left:1rem !important; padding-right:1rem !important; }
    .insight-shell { align-items:flex-start; flex-direction:column; }
}
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# Helpers
# -----------------------------
PLOT_BG = "#0a0c0e"
PLOT_PAPER = "#0a0c0e"
GRID = "rgba(190,195,200,.08)"
TEXT = "#d7d9dc"
MUTED = "#70777f"
SILVER = "#c7cbd0"
GREEN = "#78d6a3"
BLUE = "#91b7d8"
AMBER = "#e7c57a"
RED = "#e78282"


def style_fig(fig, height=390):
    fig.update_layout(
        height=height,
        paper_bgcolor=PLOT_PAPER,
        plot_bgcolor=PLOT_BG,
        font=dict(family="Inter, sans-serif", color=TEXT, size=12),
        margin=dict(l=18, r=18, t=48, b=18),
        title=dict(
            font=dict(family="Space Grotesk, sans-serif", size=16, color="#eceeef"),
            x=0.02,
            xanchor="left",
        ),
        hoverlabel=dict(
            bgcolor="#15191d",
            bordercolor="#5f666d",
            font=dict(color="#f2f3f4"),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#9da3a9"),
        ),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        linecolor="rgba(255,255,255,.08)",
        tickfont=dict(color=MUTED),
        title_font=dict(color=MUTED),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        linecolor="rgba(255,255,255,.08)",
        tickfont=dict(color=MUTED),
        title_font=dict(color=MUTED),
    )
    return fig


def plotly_config():
    return {
        "displaylogo": False,
        "responsive": True,
        "modeBarButtonsToRemove": [
            "lasso2d",
            "select2d",
            "autoScale2d",
        ],
    }


def section(eyebrow, title, description=""):
    desc = f'<div class="section-desc">{description}</div>' if description else ""
    st.markdown(
        f"""
        <div class="section-head">
            <div>
                <div class="eyebrow">{eyebrow}</div>
                <div class="section-title">{title}</div>
            </div>
            {desc}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label, value, note="", tone="neutral"):
    tone_class = {
        "green": "badge badge-green",
        "amber": "badge badge-amber",
        "neutral": "badge",
    }.get(tone, "badge")
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="small-label">{label}</div>
            <div style="font-family:'Space Grotesk';font-size:1.75rem;font-weight:700;
                        color:#f2f3f4;letter-spacing:-.045em;margin:7px 0 3px;">
                {value}
            </div>
            <span class="{tone_class}">{note}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )



# -----------------------------
# -----------------------------
# Data
# -----------------------------
DATA_FILES = [
    PROJECT_ROOT / "data" / "raw" / "users.csv",
    PROJECT_ROOT / "data" / "processed" / "clean_events.csv",
    PROJECT_ROOT / "data" / "processed" / "user_features.csv",
]

@st.cache_resource
def ensure_demo_data():
    """Generate the deterministic 20k-user dataset when deployed without data."""
    if all(path.exists() for path in DATA_FILES):
        return

    with st.spinner("Preparing the analytics dataset for the dashboard..."):
        subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "src" / "ingestion" / "generate_synthetic_data.py"),
                "--n-users",
                "20000",
                "--seed",
                "42",
                "--observation-days",
                "45",
                "--output-dir",
                str(PROJECT_ROOT / "data" / "raw"),
            ],
            cwd=str(PROJECT_ROOT),
            check=True,
        )

        subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "src" / "preprocessing" / "etl.py"),
            ],
            cwd=str(PROJECT_ROOT),
            check=True,
        )


ensure_demo_data()


@st.cache_data
def load_data():
    users = pd.read_csv(
        DATA_FILES[0],
        parse_dates=["signup_date"],
    )
    clean_events = pd.read_csv(
        DATA_FILES[1],
        parse_dates=["timestamp"],
    )
    user_features = pd.read_csv(DATA_FILES[2])
    return users, clean_events, user_features


users, clean_events, user_features = load_data()


# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown(
        """
        <div class="brand">
            <div class="brand-mark">◈</div>
            <div>
                <div class="brand-title">InsightAI</div>
                <div class="brand-sub">PRODUCT INTELLIGENCE</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    page = st.radio(
        "Workspace",
        [
            "Executive Overview",
            "Funnel",
            "Retention & Cohorts",
            "Segmentation",
            "AI Feature",
            "Experiment & Business Impact",
            "Recommendations",
        ],
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="sidebar-note">
            <b style="color:#c9cdd1;">SYNTHETIC DATASET</b><br>
            This environment uses generated product events. Results demonstrate
            analytical methodology and should not be interpreted as real-company claims.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    device_options = list(users["device"].dropna().unique())
    device_filter = st.multiselect(
        "Device",
        options=device_options,
        default=device_options,
    )

    if not device_filter:
        st.warning("Select at least one device.")
        st.stop()

    st.markdown(
        f"""
        <div class="sidebar-note">
            <span style="color:#858c93;">ACTIVE SCOPE</span><br>
            <b style="color:#e3e5e7;">{len(users[users['device'].isin(device_filter)]):,}</b>
            users
        </div>
        """,
        unsafe_allow_html=True,
    )


filtered_user_ids = users[users["device"].isin(device_filter)]["user_id"]
f_clean_events = clean_events[clean_events["user_id"].isin(filtered_user_ids)]
f_user_features = user_features[user_features["user_id"].isin(filtered_user_ids)]
f_users = users[users["user_id"].isin(filtered_user_ids)]


# -----------------------------
# Top navigation shell
# -----------------------------
st.markdown(
    f"""
    <div class="insight-shell">
        <div class="brand">
            <div class="brand-mark">◈</div>
            <div>
                <div class="brand-title">InsightAI Product Intelligence</div>
                <div class="brand-sub">AI PRODUCT • GROWTH • EXPERIMENTATION</div>
            </div>
        </div>
        <div class="status-pill">
            <span class="status-dot"></span>
            ANALYTICS ENGINE ONLINE
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# EXECUTIVE OVERVIEW
# ============================================================
if page == "Executive Overview":
    kpis = compute_kpi_summary(f_users, f_clean_events, f_user_features)

    section(
        "COMMAND CENTER",
        "Executive Overview",
        "A high-level view of activation, AI adoption and product engagement.",
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card(
            "Onboarding completion",
            f"{kpis['onboarding_completion_rate_pct']}%",
            "ACTIVATION",
            "green",
        )
    with c2:
        metric_card(
            "AI adoption",
            f"{kpis['ai_feature_penetration_pct']}%",
            "AI FEATURE",
            "neutral",
        )
    with c3:
        metric_card(
            "Free → Paid",
            f"{kpis['free_to_paid_conversion_pct']}%",
            "MONETISATION",
            "amber",
        )
    with c4:
        metric_card(
            "AI interactions / user",
            kpis["ai_interactions_per_user"],
            "ENGAGEMENT",
            "neutral",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    from metrics.kpi import compute_north_star

    ns = compute_north_star(f_clean_events).copy()

    left, right = st.columns([2.15, 1], gap="large")

    with left:
        # The metric module stores weekly windows as strings such as
        # "2025-01-20/2025-01-26". Use the window start for plotting while
        # preserving the original window in hover text.
        ns["week_window"] = ns["week"].astype(str)
        ns["week_start"] = pd.to_datetime(
            ns["week_window"].str.split("/").str[0],
            errors="coerce",
        )

        tick_step = max(1, len(ns) // 7)
        tick_values = ns["week_start"].iloc[::tick_step].tolist()

        fig = px.area(
            ns,
            x="week_start",
            y="north_star_wau",
            markers=True,
            title="North Star · Weekly active users completing an AI-assisted task",
            custom_data=["week_window"],
        )
        fig.update_traces(
            line=dict(color=SILVER, width=2),
            fillcolor="rgba(215,217,220,.10)",
            marker=dict(size=5, color="#e8eaec"),
            hovertemplate="<b>%{customdata[0]}</b><br>WAU: %{y:,}<extra></extra>",
        )
        style_fig(fig, 420)
        fig.update_xaxes(
            tickmode="array",
            tickvals=tick_values,
            ticktext=[d.strftime("%b %Y") for d in tick_values],
            tickangle=0,
            title="",
        )
        fig.update_yaxes(title="Weekly active users")
        st.plotly_chart(fig, use_container_width=True, config=plotly_config())

    with right:
        funnel_df = compute_funnel(f_clean_events, users=f_users)
        first_stage = funnel_df.iloc[0]
        last_stage = funnel_df.iloc[-1]
        bottleneck = funnel_df.iloc[-1]

        st.markdown(
            f"""
            <div class="hero-card">
                <div class="hero-kicker">Primary signal</div>
                <div class="hero-value">{bottleneck['conversion_from_previous_pct']:.2f}%</div>
                <div class="hero-note">conversion into output_saved</div>
                <br>
                <span class="badge badge-amber">FUNNEL BOTTLENECK</span>
                <br><br>
                <div style="color:#a5abb1;font-size:.78rem;line-height:1.55;">
                    {int(last_stage['users_reached']):,} users reached the final
                    meaningful-output stage from {int(first_stage['users_reached']):,}
                    signups.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    section("DECISION LAYER", "What the numbers are saying")

    a, b, c = st.columns(3)
    with a:
        metric_card(
            "Funnel bottleneck",
            "output_saved",
            "49.69% PREVIOUS-STAGE CONVERSION",
            "amber",
        )
    with b:
        metric_card(
            "Experiment signal",
            "+6.22 pp",
            "AI ONBOARDING LIFT",
            "green",
        )
    with c:
        metric_card(
            "AI penetration",
            "25.26%",
            "USERS ADOPTING AI",
            "neutral",
        )


# ============================================================
# FUNNEL
# ============================================================
elif page == "Funnel":
    section(
        "ACTIVATION",
        "Onboarding & Activation Funnel",
        "Trace the user journey from signup to a meaningful saved AI output.",
    )

    funnel_df = compute_funnel(f_clean_events, users=f_users)

    left, right = st.columns([1.65, 1], gap="large")

    with left:
        fig = px.funnel(
            funnel_df,
            x="users_reached",
            y="stage",
            title="User progression",
        )
        fig.update_traces(
            marker=dict(
                color=[
                    "#cfd2d5",
                    "#b8bdc2",
                    "#a1a7ad",
                    "#898f95",
                    "#71777d",
                    "#d8b96f",
                ]
            ),
            textinfo="value+percent initial",
        )
        style_fig(fig, 510)
        st.plotly_chart(fig, use_container_width=True, config=plotly_config())

    with right:
        bottleneck = funnel_df.iloc[-1]
        st.markdown(
            f"""
            <div class="hero-card">
                <div class="hero-kicker">Largest drop-off</div>
                <div style="font-family:'Space Grotesk';font-size:1.45rem;font-weight:700;
                            color:#f1f2f3;margin:7px 0;">
                    {bottleneck['stage']}
                </div>
                <div class="hero-value">{bottleneck['conversion_from_previous_pct']:.2f}%</div>
                <div class="hero-note">previous-stage conversion</div>
                <br>
                <span class="badge badge-amber">INVESTIGATE</span>
                <p style="margin-top:14px;font-size:.8rem;line-height:1.6;color:#858c93;">
                    The funnel identifies where users stop progressing. It does not
                    establish why they stop. Quality, workflow friction, latency and
                    unclear next actions require further investigation.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.dataframe(
        funnel_df,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    section("EXPERIMENT SPLIT", "Funnel by experiment group")

    seg_funnel = compute_funnel(
        f_clean_events,
        users=f_users,
        segment_col="experiment_group",
    )

    fig = px.bar(
        seg_funnel,
        x="stage",
        y="users_reached",
        color="experiment_group",
        barmode="group",
        title="Control vs treatment progression",
    )
    fig.update_layout(xaxis_tickangle=-25)
    style_fig(fig, 390)
    st.plotly_chart(fig, use_container_width=True, config=plotly_config())


# ============================================================
# RETENTION
# ============================================================
elif page == "Retention & Cohorts":
    section(
        "RETENTION",
        "Retention & Cohort Analysis",
        "Understand whether users continue returning after acquisition and activation.",
    )

    st.markdown(
        '<span class="badge badge-amber">OBSERVATIONAL · NOT CAUSAL</span>',
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    retention_curve = compute_retention_curve(f_clean_events, f_users)

    fig = px.area(
        retention_curve,
        x="day",
        y="retention_pct",
        markers=True,
        title="Retention curve",
    )
    fig.update_traces(
        line=dict(color=SILVER, width=2),
        fillcolor="rgba(215,217,220,.09)",
        marker=dict(size=5, color="#e5e7e9"),
    )
    style_fig(fig, 420)
    st.plotly_chart(fig, use_container_width=True, config=plotly_config())

    cohort_cmp = compute_behavioural_cohort_comparison(
        f_user_features,
        f_clean_events,
        f_users,
        day=30,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    section("BEHAVIOURAL COHORT", "D30 retention by AI adoption")

    if len(cohort_cmp) > 0:
        display_cmp = cohort_cmp.copy()
        st.dataframe(display_cmp, use_container_width=True, hide_index=True)

        fig = px.bar(
            display_cmp,
            x=display_cmp.columns[0],
            y=display_cmp.columns[-1],
            title="AI adopters vs non-adopters",
            text_auto=True,
        )
        fig.update_traces(marker_color=SILVER)
        style_fig(fig, 350)
        st.plotly_chart(fig, use_container_width=True, config=plotly_config())

    st.info(
        "The AI adopter vs non-adopter comparison is observational. "
        "Different user characteristics may explain part of the retention gap."
    )


# ============================================================
# SEGMENTATION
# ============================================================
elif page == "Segmentation":
    section(
        "USER INTELLIGENCE",
        "Behavioural Segmentation",
        "Compare interpretable usage tiers with machine-learning-based behavioural clusters.",
    )

    feats = build_segmentation_features(
        f_users,
        f_clean_events,
        f_user_features,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("Rule-based tiers")

    rule_df = rule_based_segments(feats)
    seg_counts = rule_df["rule_based_segment"].value_counts().reset_index()
    seg_counts.columns = ["segment", "n_users"]

    # Keep the full analytical label in hover while using compact display labels.
    seg_counts["display_segment"] = (
        seg_counts["segment"]
        .astype(str)
        .str.replace(r"\s*\(.*?\)", "", regex=True)
        .str.replace("_", " ")
        .str.title()
    )

    left, right = st.columns([1.35, 1], gap="large")

    with left:
        fig = px.bar(
            seg_counts,
            x="display_segment",
            y="n_users",
            title="Users by behavioural tier",
            text_auto=True,
            custom_data=["segment"],
        )
        fig.update_traces(
            hovertemplate="<b>%{customdata[0]}</b><br>Users: %{y:,}<extra></extra>"
        )
        fig.update_traces(marker_color=SILVER)
        style_fig(fig, 370)
        fig.update_xaxes(
            title="",
            tickangle=0,
            automargin=True,
        )
        fig.update_yaxes(title="Users")
        st.plotly_chart(fig, use_container_width=True, config=plotly_config())

    with right:
        total = max(seg_counts["n_users"].sum(), 1)
        top_segment = seg_counts.iloc[0]
        metric_card(
            "Largest segment",
            str(top_segment["segment"]).upper(),
            f"{int(top_segment['n_users']):,} USERS · {top_segment['n_users']/total:.1%}",
            "neutral",
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("K-Means clusters")

    n_clusters = st.slider(
        "Number of clusters",
        min_value=2,
        max_value=6,
        value=4,
    )

    if len(feats) >= n_clusters:
        cluster_df, feature_cols = kmeans_segments(
            feats,
            n_clusters=n_clusters,
        )
        profile = profile_clusters(cluster_df, feature_cols)
        profile["suggested_action"] = profile.apply(
            lambda row: suggest_cluster_action(row, profile),
            axis=1,
        )

        st.dataframe(
            profile,
            use_container_width=True,
            hide_index=True,
        )

        st.info(compare_segmentations(rule_df, profile))
    else:
        st.warning("Not enough users in the current filter to run clustering.")


# ============================================================
# AI FEATURE
# ============================================================
elif page == "AI Feature":
    section(
        "AI PRODUCT",
        "AI Feature Analytics",
        "Measure adoption, operational quality proxies and AI economics without confusing usage with value.",
    )

    adoption = compute_adoption(f_user_features)
    quality = compute_quality(f_clean_events)
    cost = compute_cost(f_clean_events, f_user_features)

    adoption_value = adoption.get("ai_adoption_pct", adoption.get("adoption_pct", 0))
    adopter_count = adoption.get("n_adopters", adoption.get("ai_adopters", 0))

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_card(
            "AI adoption",
            f"{adoption_value:.2f}%",
            f"{int(adopter_count):,} ADOPTERS",
            "green",
        )

    with c2:
        metric_card(
            "AI quality",
            "PROXY",
            "RESPONSE / RATING SIGNALS",
            "amber",
        )

    with c3:
        cost_value = cost.get("total_ai_cost_usd", cost.get("ai_cost_usd", 0))
        metric_card(
            "AI cost",
            f"${cost_value:,.2f}",
            "SYNTHETIC ECONOMIC MODEL",
            "neutral",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")

    with left:
        with st.container(border=True):
            st.subheader("Adoption evidence")
            st.json(adoption)

    with right:
        with st.container(border=True):
            st.subheader("Quality proxy metrics")
            st.json(quality)

    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader("AI economics")
        st.json(cost)

    st.info(
        "Current quality metrics are proxies. Production AI evaluation should add "
        "task success, semantic quality, groundedness, hallucination, latency and "
        "cost per successful task."
    )


# ============================================================
# EXPERIMENT + BUSINESS IMPACT
# ============================================================
elif page == "Experiment & Business Impact":
    section(
        "EXPERIMENTATION",
        "AI-Assisted Onboarding",
        "Evaluate activation using a randomized control/treatment comparison.",
    )

    activated_users = set(
        f_clean_events.loc[
            f_clean_events["event_name"] == "onboarding_completed",
            "user_id",
        ]
    )

    exp_users = f_users.copy()
    exp_users["activated"] = exp_users["user_id"].isin(activated_users)

    control = exp_users[exp_users["experiment_group"] == "control"]
    treatment = exp_users[exp_users["experiment_group"] == "treatment"]

    result = two_proportion_z_test(
        success_a=int(control["activated"].sum()),
        n_a=len(control),
        success_b=int(treatment["activated"].sum()),
        n_b=len(treatment),
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card(
            "Control activation",
            f"{result['control_rate_pct']:.2f}%",
            f"N={len(control):,}",
            "neutral",
        )
    with c2:
        metric_card(
            "Treatment activation",
            f"{result['treatment_rate_pct']:.2f}%",
            f"N={len(treatment):,}",
            "green",
        )
    with c3:
        metric_card(
            "Activation lift",
            f"+{result['absolute_lift_pp']:.2f} pp",
            "TREATMENT − CONTROL",
            "green",
        )
    with c4:
        metric_card(
            "Statistical signal",
            "<0.001" if result["p_value"] < 0.001 else f"{result['p_value']:.3g}",
            "P-VALUE",
            "green" if result["p_value"] < 0.05 else "neutral",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    rates = pd.DataFrame(
        {
            "group": ["Control", "Treatment"],
            "activation_rate": [
                result["control_rate_pct"],
                result["treatment_rate_pct"],
            ],
        }
    )

    fig = px.bar(
        rates,
        x="group",
        y="activation_rate",
        text="activation_rate",
        title="Activation rate by experiment group",
    )
    fig.update_traces(
        marker_color=[SILVER, "#f0f1f2"],
        texttemplate="%{text:.2f}%",
        textposition="outside",
    )
    style_fig(fig, 370)
    fig.update_yaxes(title="Activation rate (%)")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config())

    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-kicker">Experiment result</div>
            <div class="hero-value">+{result['absolute_lift_pp']:.2f} pp</div>
            <div class="hero-note">
                95% CI: {result['ci_95_absolute_lift_pp']} pp
                &nbsp; · &nbsp; Cohen's h: {result['cohens_h']}
            </div>
            <br>
            <span class="badge badge-green">STATISTICALLY SIGNIFICANT</span>
            <p style="margin-top:13px;color:#858c93;font-size:.78rem;line-height:1.55;">
                This result is generated from the project's synthetic randomized
                experiment. The data generator deliberately embeds a positive treatment
                effect, so the result validates the analysis pipeline rather than proving
                a real-world product effect.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    section("BUSINESS IMPACT", "AI economics")

    ai_cost = compute_cost(f_clean_events, f_user_features)
    impact = compute_business_impact(f_user_features, ai_cost)

    roi = impact.get("roi_pct", impact.get("illustrative_roi_pct", None))
    if roi is not None:
        metric_card(
            "Illustrative ROI",
            f"{float(roi):,.1f}%",
            "SYNTHETIC ASSUMPTIONS",
            "amber",
        )

    st.json(impact)

    st.warning(
        "ROI is illustrative and depends on synthetic revenue, cost and attribution "
        "assumptions. It is not a measured real-world financial return."
    )

    st.markdown("<br>", unsafe_allow_html=True)
    section("SEGMENT CHECK", "Treatment effect by device")

    seg = segmented_ab_results(f_users, f_clean_events, "device")
    if isinstance(seg, pd.DataFrame) and not seg.empty:
        st.dataframe(seg, use_container_width=True, hide_index=True)

        note = summarize_heterogeneity(seg, "device")
        st.info(note)


# ============================================================
# RECOMMENDATIONS
# ============================================================
elif page == "Recommendations":
    section(
        "DECISION INTELLIGENCE",
        "Evidence-Based Recommendations",
        "Convert measured signals into product actions while exposing where analyst judgement enters.",
    )

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-kicker">Decision framework</div>
            <div style="font-family:'Space Grotesk';font-size:1.4rem;font-weight:700;
                        color:#f1f2f3;margin:6px 0;">
                Observe → Diagnose → Experiment → Evaluate → Quantify → Prioritise
            </div>
            <div class="hero-note">
                The engine surfaces evidence. It does not replace product judgement.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    funnel_df = compute_funnel(f_clean_events, users=f_users)

    activated_users = set(
        f_clean_events.loc[
            f_clean_events["event_name"] == "onboarding_completed",
            "user_id",
        ]
    )

    exp_users = f_users.copy()
    exp_users["activated"] = exp_users["user_id"].isin(activated_users)

    control = exp_users[exp_users["experiment_group"] == "control"]
    treatment = exp_users[exp_users["experiment_group"] == "treatment"]

    ab_result = two_proportion_z_test(
        success_a=int(control["activated"].sum()),
        n_a=len(control),
        success_b=int(treatment["activated"].sum()),
        n_b=len(treatment),
    )

    seg = segmented_ab_results(f_users, f_clean_events, "device")
    heterogeneity_note = summarize_heterogeneity(seg, "device")

    adoption = compute_adoption(f_user_features)
    ai_cost = compute_cost(f_clean_events, f_user_features)
    impact = compute_business_impact(f_user_features, ai_cost)

    recs = generate_recommendations(
        funnel_df,
        ab_result,
        adoption,
        impact,
        heterogeneity_note,
    )

    for r in recs:
        confidence = r["confidence"]
        badge_class = {
            "High": "badge-green",
            "Medium": "badge-amber",
            "Low": "",
        }.get(confidence, "")

        st.markdown(
            f"""
            <div class="glass-card" style="margin-top:14px;">
                <span class="badge {badge_class}">{confidence} CONFIDENCE</span>
                <div style="font-family:'Space Grotesk';font-size:1.12rem;font-weight:700;
                            color:#e9ebed;margin:11px 0 6px;">
                    {r['recommendation']}
                </div>
                <div style="color:#7e858c;font-size:.77rem;">
                    Trigger · {r['trigger']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("Inspect evidence"):
            evidence = r["evidence"]
            cols = st.columns(min(4, max(1, len(evidence))))

            for idx, (key, value) in enumerate(evidence.items()):
                label = key.replace("_", " ").title()

                if key == "p_value" and isinstance(value, (int, float)):
                    display_value = f"{value:.3g}"
                elif isinstance(value, float):
                    display_value = f"{value:.2f}"
                else:
                    display_value = value

                with cols[idx % len(cols)]:
                    st.metric(label, display_value)

    st.markdown("<br>", unsafe_allow_html=True)
    section(
        "PRIORITISATION",
        "RICE-Scored Roadmap",
        "A structured prioritisation model with explicit disclosure of analyst estimates.",
    )

    st.caption(
        "Reach and Confidence for onboarding are grounded in the project's funnel/experiment "
        "data. Impact and Effort for every initiative, and Confidence for the other four, "
        "are analyst estimates."
    )

    rice_table = build_initiative_table(
        funnel_df,
        ab_result,
        total_users=len(f_users),
    )

    rice_display = rice_table[
        [
            "initiative",
            "reach",
            "impact",
            "confidence",
            "effort",
            "rice_score",
        ]
    ].copy()

    rice_display["reach"] = (
        rice_display["reach"].round(0).astype(int)
    )
    rice_display["confidence"] = rice_display["confidence"].apply(
        lambda x: f"{x:.0%}"
    )
    rice_display["impact"] = rice_display["impact"].round(1)
    rice_display["effort"] = rice_display["effort"].round(1)
    rice_display["rice_score"] = rice_display["rice_score"].round(1)

    rice_display = rice_display.rename(
        columns={
            "initiative": "Initiative",
            "reach": "Reach",
            "impact": "Impact",
            "confidence": "Confidence",
            "effort": "Effort",
            "rice_score": "RICE Score",
        }
    )

    st.dataframe(
        rice_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Initiative": st.column_config.TextColumn("Initiative", width="large"),
            "Reach": st.column_config.NumberColumn("Reach", format="%d"),
            "Impact": st.column_config.NumberColumn("Impact", format="%.1f"),
            "Confidence": st.column_config.TextColumn("Confidence"),
            "Effort": st.column_config.NumberColumn("Effort", format="%.1f"),
            "RICE Score": st.column_config.NumberColumn("RICE Score", format="%.1f"),
        },
    )

    with st.expander("View confidence basis"):
        for _, row in rice_table.iterrows():
            st.markdown(f"**{row['initiative']}**")
            st.caption(row["confidence_basis"])


# -----------------------------
# Footer
# -----------------------------
st.markdown(
    """
    <br><br>
    <div style="border-top:1px solid rgba(210,215,220,.09);padding-top:14px;
                display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;">
        <span style="font-size:.65rem;color:#555c63;letter-spacing:.12em;">
            INSIGHTAI · PRODUCT DECISION INTELLIGENCE
        </span>
        <span style="font-size:.65rem;color:#555c63;">
            Synthetic data · Analytical demonstration
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)
