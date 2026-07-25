"""
dashboard.py — Real-time Streamlit Dashboard
Honeywell Campus Hackathon — Eco-Loop Building Agents

Shows live building telemetry and AI vs baseline comparison.

Usage:
  streamlit run dashboard.py
"""

import os
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import LOG_FILE, BASELINE_LOG, PMV_MIN, PMV_MAX

# ──────────────────────────────────────────────
# PAGE SETUP
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Eco-Loop Building Agents",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# CUSTOM CSS — dark, Grafana-style, animated
# ──────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes livePulse {
    0%   { box-shadow: 0 0 0 0 rgba(16,229,163,0.55); }
    70%  { box-shadow: 0 0 0 8px rgba(16,229,163,0); }
    100% { box-shadow: 0 0 0 0 rgba(16,229,163,0); }
  }
  @keyframes glowCycle {
    0%, 100% { box-shadow: 0 0 0px rgba(0,212,255,0); }
    50%      { box-shadow: 0 0 14px rgba(0,212,255,0.18); }
  }

  [data-testid="stApp"], .main, .block-container {
    background: radial-gradient(ellipse at top, #10141F 0%, #0A0D14 60%, #06080D 100%) !important;
    color: #E6EDF3 !important;
  }

  .hero {
    background: linear-gradient(135deg, #12172A 0%, #0D1220 100%);
    border: 1px solid rgba(0,212,255,0.25);
    box-shadow: 0 0 24px rgba(0,102,255,0.12), inset 0 1px 0 rgba(255,255,255,0.03);
    border-radius: 14px;
    padding: 1.8rem 2.5rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
    justify-content: space-between;
    animation: fadeInUp 0.5s ease-out;
  }
  .hero-left { display: flex; align-items: center; gap: 1.5rem; }
  .hero h1 {
    font-size: 2.1rem;
    font-weight: 800;
    background: linear-gradient(90deg, #00D4FF, #A78BFA 55%, #FF4FD8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
  }
  .hero p { color: #8B96A8; margin: 0; font-size: 0.95rem; }
  .live-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(16,229,163,0.08);
    border: 1px solid rgba(16,229,163,0.4);
    color: #10E5A3;
    font-size: 0.78rem; font-weight: 700; letter-spacing: 1.5px;
    padding: 6px 14px; border-radius: 999px;
  }
  .live-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: #10E5A3;
    animation: livePulse 1.6s infinite;
  }

  .metric-card {
    background: linear-gradient(160deg, #131A28 0%, #0E141F 100%);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    text-align: left;
    transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
    animation: fadeInUp 0.5s ease-out both;
  }
  .metric-card:hover {
    transform: translateY(-3px);
    border-color: rgba(0,212,255,0.4);
    box-shadow: 0 8px 24px rgba(0,0,0,0.4), 0 0 16px rgba(0,212,255,0.15);
  }
  .metric-top { display:flex; align-items:center; justify-content:space-between; }
  .metric-value { font-size: 1.9rem; font-weight: 800; color: #F0F4F8; letter-spacing: -0.5px; }
  .metric-label { font-size: 0.72rem; color: #6E7B90; text-transform: uppercase; letter-spacing: 1.4px; margin-top: 2px;}
  .metric-sub   { font-size: 0.82rem; margin-top: 6px; font-weight: 600; }
  .metric-icon  { font-size: 1.4rem; opacity: 0.85; }

  .accent-cyan   { border-top: 3px solid #00D4FF; }
  .accent-green  { border-top: 3px solid #10E5A3; }
  .accent-amber  { border-top: 3px solid #FFB020; }
  .accent-magenta{ border-top: 3px solid #FF4FD8; }
  .accent-violet { border-top: 3px solid #A78BFA; }

  .badge-ok   { color: #10E5A3; font-weight: 700; }
  .badge-warn { color: #FFB020; font-weight: 700; }
  .badge-bad  { color: #FF5A7A; font-weight: 700; }

  .section-header {
    font-size: 1.05rem;
    font-weight: 700;
    color: #E6EDF3;
    border-left: 4px solid #00D4FF;
    padding-left: 12px;
    margin: 1.8rem 0 1rem 0;
    animation: fadeInUp 0.5s ease-out both;
  }

  .stPlotlyChart {
    background: transparent !important;
    border-radius: 12px;
    animation: glowCycle 6s ease-in-out infinite;
  }

  [data-testid="stSidebar"] {
    background-color: #0B0F17 !important;
    border-right: 1px solid rgba(255,255,255,0.06);
  }
  [data-testid="stSidebar"] * { color: #AEB8C8 !important; }
  [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #F0F4F8 !important;
    font-weight: 700;
  }
  [data-testid="stWidgetLabel"] p { color: #E6EDF3 !important; font-weight: 600; }

  .agent-log {
    background: #0B0F17;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 12px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #AEB8C8;
    max-height: 280px;
    overflow-y: auto;
    animation: fadeInUp 0.6s ease-out both;
  }
  .agent-log .ts  { color: #00D4FF; font-weight: 700; }
  .agent-log .act { color: #A78BFA; font-weight: 700; }
  .agent-log .rsn { color: #C6D0DC; }
  .agent-log div  { border-bottom: 1px solid rgba(255,255,255,0.04); padding-bottom: 6px; }

  [data-testid="stMetric"] {
    background: linear-gradient(160deg, #131A28 0%, #0E141F 100%);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 1rem 1.2rem;
    animation: fadeInUp 0.6s ease-out both;
  }
  [data-testid="stMetricLabel"] { color: #6E7B90 !important; }
  [data-testid="stMetricValue"] { color: #F0F4F8 !important; }
  [data-testid="stMetricDelta"] { color: #10E5A3 !important; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# DATA LOADING
# ──────────────────────────────────────────────
@st.cache_data(ttl=2)
def load_ai_data():
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame()
    try:
        df = pd.read_csv(LOG_FILE)
        return df[df["run_type"].isin(["ai", "rule"])] if "run_type" in df.columns else df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=2)
def load_baseline_data():
    if not os.path.exists(BASELINE_LOG):
        return pd.DataFrame()
    try:
        return pd.read_csv(BASELINE_LOG)
    except Exception:
        return pd.DataFrame()


# ──────────────────────────────────────────────
# COLOUR PALETTE
# ──────────────────────────────────────────────
C_AI       = "#00D4FF"    # Electric cyan — AI zone temp
C_OUTDOOR  = "#FFB020"    # Amber — outdoor temp
C_PMV      = "#FF4FD8"    # Magenta — PMV line
C_BASELINE = "#6E7B90"    # Muted slate — baseline series
C_PMV_OK   = "#10E5A3"    # Emerald green — comfortable / savings
C_PMV_BAD  = "#FF5A7A"    # Rose — discomfort / alerts
C_HVAC     = "#A78BFA"    # Violet — HVAC power bars
C_BG       = "#0E1420"    # Dark chart canvas
C_GRID     = "rgba(255,255,255,0.08)"

PLOT_LAYOUT = dict(
    paper_bgcolor=C_BG,
    plot_bgcolor =C_BG,
    font=dict(family="Inter", color="#AEB8C8", size=12),
    title_font=dict(color="#F0F4F8", size=14),
    xaxis=dict(gridcolor=C_GRID, zerolinecolor=C_GRID, linecolor="rgba(255,255,255,0.15)"),
    yaxis=dict(gridcolor=C_GRID, zerolinecolor=C_GRID, linecolor="rgba(255,255,255,0.15)"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.1)", font=dict(color="#AEB8C8")),
    hoverlabel=dict(bgcolor="#161B22", font_color="#E6EDF3", bordercolor=C_AI),
)


# ──────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Controls")
    auto_refresh = st.toggle("Auto-refresh (2s)", value=True)
    show_baseline = st.toggle("Show baseline comparison", value=True)

    st.markdown("---")
    st.markdown("### 📋 About")
    st.markdown("""
**Eco-Loop Building Agents**

Autonomous AI feedback loop:
- 🏢 EnergyPlus building sim
- 🧠 Ollama LLM (Qwen2.5-7B)
- 🔧 MCP Tool layer
- ♻️ Closed-loop control

**Target PMV:** -0.5 → +0.5
""")

    st.markdown("---")
    st.markdown("### 🎨 Legend")
    st.markdown("""
<div style="font-size:0.85rem; line-height:1.9;">
<span style="color:#00D4FF">●</span> AI Zone Temp&nbsp;&nbsp;
<span style="color:#FFB020">●</span> Outdoor<br>
<span style="color:#FF4FD8">●</span> PMV&nbsp;&nbsp;
<span style="color:#10E5A3">●</span> Savings / Comfort<br>
<span style="color:#A78BFA">●</span> HVAC Power&nbsp;&nbsp;
<span style="color:#6E7B90">●</span> Baseline
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📁 Log Files")
    st.code(f"AI:       {LOG_FILE} \nBaseline: {BASELINE_LOG}")


# ──────────────────────────────────────────────
# HERO HEADER
# ──────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div class="hero-left">
    <div style="font-size:3rem">🏢</div>
    <div>
      <h1>Eco-Loop Building Agents</h1>
      <p>Autonomous AI-Driven HVAC Optimization · Real-time Dashboard</p>
    </div>
  </div>
  <div class="live-badge"><span class="live-dot"></span> LIVE</div>
</div>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# LOAD DATA
# ──────────────────────────────────────────────
ai_df   = load_ai_data()
base_df = load_baseline_data()

has_ai   = not ai_df.empty
has_base = not base_df.empty

if not has_ai:
    st.info("⏳ Waiting for data... Run `python main.py` to start the AI agent loop.")
    if auto_refresh:
        time.sleep(2)
        st.rerun()
    st.stop()


# ──────────────────────────────────────────────
# KPI CARDS
# ──────────────────────────────────────────────
last = ai_df.iloc[-1]

# Energy savings calculation
ai_energy   = last.get("energy_kwh", 0)
base_energy = base_df.iloc[-1]["energy_kwh"] if has_base else None
savings_pct = (
    round((1 - ai_energy / base_energy) * 100, 1)
    if base_energy and base_energy > 0 else None
)

pmv_ok_pct = round(ai_df["comfort_ok"].mean() * 100, 1) if "comfort_ok" in ai_df.columns else "N/A"

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card accent-cyan">
      <div class="metric-top"><span class="metric-icon">🌡️</span></div>
      <div class="metric-value">{last.get('avg_zone_temp_c', '—')}°C</div>
      <div class="metric-label">Zone Temp</div>
      <div class="metric-sub" style="color:#FFB020">outdoor: {last.get('outdoor_temp_c', '—')}°C</div>
    </div>""", unsafe_allow_html=True)

with col2:
    pmv = last.get('pmv', 0)
    badge = "badge-ok" if PMV_MIN <= (pmv or 0) <= PMV_MAX else "badge-bad"
    st.markdown(f"""
    <div class="metric-card accent-magenta">
      <div class="metric-top"><span class="metric-icon">🧭</span></div>
      <div class="metric-value">{pmv:+.2f}</div>
      <div class="metric-label">Current PMV</div>
      <div class="metric-sub {badge}">{last.get('comfort_ok') and 'Comfortable ✅' or 'Discomfort ⚠️'}</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card accent-violet">
      <div class="metric-top"><span class="metric-icon">⚡</span></div>
      <div class="metric-value">{ai_energy:.3f}</div>
      <div class="metric-label">Energy Used (kWh)</div>
      <div class="metric-sub" style="color:#A78BFA">HVAC: {last.get('hvac_kw', '—')} kW</div>
    </div>""", unsafe_allow_html=True)

with col4:
    sv = f"{savings_pct}%" if savings_pct is not None else "Run baseline"
    sv_color = "#10E5A3" if savings_pct and savings_pct > 0 else "#FFB020"
    st.markdown(f"""
    <div class="metric-card accent-green">
      <div class="metric-top"><span class="metric-icon">🌱</span></div>
      <div class="metric-value" style="color:{sv_color}">{sv}</div>
      <div class="metric-label">Energy Savings</div>
      <div class="metric-sub" style="color:#6E7B90">vs fixed setpoint</div>
    </div>""", unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-card accent-amber">
      <div class="metric-top"><span class="metric-icon">😊</span></div>
      <div class="metric-value">{pmv_ok_pct}%</div>
      <div class="metric-label">Comfort Rate</div>
      <div class="metric-sub" style="color:#6E7B90">timesteps in target</div>
    </div>""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# ROW 2: ZONE TEMP + PMV
# ──────────────────────────────────────────────
st.markdown('<div class="section-header">📈 Building Telemetry</div>', unsafe_allow_html=True)

col_a, col_b = st.columns(2)

with col_a:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ai_df["timestep"], y=ai_df["avg_zone_temp_c"],
        name="AI Zone Temp", line=dict(color=C_AI, width=3),
        mode="lines+markers", marker=dict(size=5, color=C_AI),
        fill="tozeroy", fillcolor="rgba(0,212,255,0.12)"
    ))
    fig.add_trace(go.Scatter(
        x=ai_df["timestep"], y=ai_df["outdoor_temp_c"],
        name="Outdoor Temp", line=dict(color=C_OUTDOOR, width=2, dash="dot"),
        mode="lines+markers", marker=dict(size=4, color=C_OUTDOOR)
    ))
    if has_base and show_baseline:
        fig.add_trace(go.Scatter(
            x=base_df["timestep"], y=base_df["avg_zone_temp_c"],
            name="Baseline Zone", line=dict(color=C_BASELINE, width=1.5, dash="dash")
        ))
    fig.update_layout(
        title="Zone & Outdoor Temperature (°C)",
        yaxis_title="Temperature (°C)",
        **PLOT_LAYOUT
    )
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    fig2 = go.Figure()
    # Comfort band
    fig2.add_hrect(
        y0=PMV_MIN, y1=PMV_MAX,
        fillcolor="rgba(16,229,163,0.10)",
        line_width=0, annotation_text="Comfort Zone",
        annotation_position="top left",
        annotation_font_color=C_PMV_OK
    )
    fig2.add_trace(go.Scatter(
        x=ai_df["timestep"], y=ai_df["pmv"],
        name="AI PMV", line=dict(color=C_PMV, width=2.5),
        mode="lines+markers",
        marker=dict(
            color=[C_PMV_OK if PMV_MIN <= v <= PMV_MAX else C_PMV_BAD
                   for v in ai_df["pmv"]],
            size=7, line=dict(width=1, color="#0E1420")
        )
    ))
    if has_base and show_baseline:
        fig2.add_trace(go.Scatter(
            x=base_df["timestep"], y=base_df["pmv"],
            name="Baseline PMV", line=dict(color=C_BASELINE, width=1.5, dash="dash")
        ))
    fig2.add_hline(y=PMV_MIN, line_dash="dot", line_color=C_PMV_OK, line_width=1)
    fig2.add_hline(y=PMV_MAX, line_dash="dot", line_color=C_PMV_OK, line_width=1)
    fig2.update_layout(
        title="PMV Thermal Comfort Index",
        yaxis_title="PMV",
        yaxis_range=[-2, 2],
        **PLOT_LAYOUT
    )
    st.plotly_chart(fig2, use_container_width=True)


# ──────────────────────────────────────────────
# ROW 3: ENERGY COMPARISON + CUMULATIVE
# ──────────────────────────────────────────────
st.markdown('<div class="section-header">⚡ Energy Analysis</div>', unsafe_allow_html=True)

col_c, col_d = st.columns(2)

with col_c:
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=ai_df["timestep"], y=ai_df["energy_kwh"],
        name="AI Agent", line=dict(color=C_PMV_OK, width=3),
        mode="lines+markers", marker=dict(size=5, color=C_PMV_OK),
        fill="tozeroy", fillcolor="rgba(16,229,163,0.12)"
    ))
    if has_base and show_baseline:
        fig3.add_trace(go.Scatter(
            x=base_df["timestep"], y=base_df["energy_kwh"],
            name="Baseline (Fixed Setpoint)",
            line=dict(color=C_BASELINE, width=2, dash="dash"),
            fill="tozeroy", fillcolor="rgba(110,123,144,0.06)"
        ))
    fig3.update_layout(
        title="Cumulative Energy Consumption (kWh)",
        yaxis_title="kWh",
        **PLOT_LAYOUT
    )
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    fig4 = go.Figure()
    # Color bars on a gradient scale so spikes stand out (like the reference dashboard)
    hvac_vals = ai_df["hvac_kw"]
    fig4.add_trace(go.Bar(
        x=ai_df["timestep"], y=hvac_vals,
        name="HVAC Power (kW)",
        marker=dict(
            color=hvac_vals,
            colorscale=[[0, "#00D4FF"], [0.5, "#A78BFA"], [1, "#FF4FD8"]],
            line=dict(width=0),
        ),
    ))
    fig4.update_layout(
        title="HVAC Power Draw per Timestep (kW)",
        yaxis_title="kW",
        **PLOT_LAYOUT
    )
    st.plotly_chart(fig4, use_container_width=True)


# ──────────────────────────────────────────────
# ROW 4: AGENT DECISIONS LOG
# ──────────────────────────────────────────────
if "reasoning" in ai_df.columns:
    st.markdown('<div class="section-header">🤖 Agent Decision Log</div>', unsafe_allow_html=True)

    recent = ai_df.tail(15)[["timestep", "hour", "pmv", "energy_kwh", "reasoning"]].iloc[::-1]
    log_html = '<div class="agent-log">'
    for _, row in recent.iterrows():
        pmv_color = "#64ffda" if PMV_MIN <= (row.get("pmv") or 0) <= PMV_MAX else "#ef5350"
        log_html += (
            f'<div style="margin-bottom:8px">'
            f'<span class="ts">[T{int(row.get("timestep", 0)):03d} h{row.get("hour", 0):.0f}]</span> '
            f'<span style="color:{pmv_color}">PMV={row.get("pmv", 0):+.2f}</span> '
            f'<span style="color:#7b2ff7">⚡{row.get("energy_kwh", 0):.3f}kWh</span> '
            f'<span class="rsn">→ {row.get("reasoning", "")}</span>'
            f'</div>'
        )
    log_html += '</div>'
    st.markdown(log_html, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# SAVINGS SUMMARY BOX
# ──────────────────────────────────────────────
if has_base and savings_pct is not None:
    st.markdown('<div class="section-header">🏆 Results Summary</div>', unsafe_allow_html=True)

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("AI Energy Used",       f"{ai_energy:.3f} kWh")
    with col_s2:
        st.metric("Baseline Energy Used", f"{base_energy:.3f} kWh")
    with col_s3:
        st.metric("Energy Saved",         f"{savings_pct}%",
                  delta=f"{base_energy - ai_energy:.3f} kWh saved")


# ──────────────────────────────────────────────
# AUTO REFRESH
# ──────────────────────────────────────────────
if auto_refresh:
    time.sleep(2)
    st.rerun()
