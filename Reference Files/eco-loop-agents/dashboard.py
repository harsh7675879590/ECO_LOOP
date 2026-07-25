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

from config import LOG_FILE, BASELINE_LOG, PMV_MIN, PMV_MAX

# ──────────────────────────────────────────────
# PAGE SETUP
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="Eco-Loop Building Agents",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# CUSTOM CSS
# ──────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
  }

  .main { background: #0a0e1a; }

  /* Header */
  .hero {
    background: linear-gradient(135deg, #1a1f3a 0%, #0f2027 50%, #0a0e1a 100%);
    border: 1px solid rgba(0, 212, 255, 0.2);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
  }
  .hero h1 {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(90deg, #00d4ff, #7b2ff7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
  }
  .hero p { color: #8892b0; margin: 0; font-size: 0.95rem; }

  /* Metric cards */
  .metric-card {
    background: linear-gradient(145deg, #141929, #0f1624);
    border: 1px solid rgba(123, 47, 247, 0.3);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    transition: border-color 0.3s;
  }
  .metric-card:hover { border-color: rgba(0, 212, 255, 0.6); }
  .metric-value { font-size: 2rem; font-weight: 700; color: #00d4ff; }
  .metric-label { font-size: 0.8rem; color: #8892b0; text-transform: uppercase; letter-spacing: 1px; }
  .metric-sub   { font-size: 0.9rem; color: #64ffda; margin-top: 4px; }

  /* Status badges */
  .badge-ok   { color: #64ffda; font-weight: 600; }
  .badge-warn { color: #ffa726; font-weight: 600; }
  .badge-bad  { color: #ef5350; font-weight: 600; }

  /* Section headers */
  .section-header {
    font-size: 1.1rem;
    font-weight: 700;
    color: #ccd6f6;
    border-left: 3px solid #7b2ff7;
    padding-left: 12px;
    margin: 1.5rem 0 1rem 0;
  }

  /* Sidebar */
  section[data-testid="stSidebar"] {
    background: #0f1624;
    border-right: 1px solid rgba(123, 47, 247, 0.2);
  }

  /* Agent log */
  .agent-log {
    background: #0d1117;
    border: 1px solid rgba(100, 255, 218, 0.15);
    border-radius: 8px;
    padding: 12px 16px;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    color: #8892b0;
    max-height: 260px;
    overflow-y: auto;
  }
  .agent-log .ts  { color: #7b2ff7; }
  .agent-log .act { color: #64ffda; }
  .agent-log .rsn { color: #ccd6f6; }
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
C_AI       = "#00d4ff"
C_BASELINE = "#ffa726"
C_PMV_OK   = "#64ffda"
C_PMV_BAD  = "#ef5350"
C_BG       = "#0a0e1a"
C_GRID     = "rgba(255,255,255,0.05)"

PLOT_LAYOUT = dict(
    paper_bgcolor=C_BG,
    plot_bgcolor =C_BG,
    font=dict(family="Inter", color="#8892b0", size=12),
    xaxis=dict(gridcolor=C_GRID, zerolinecolor=C_GRID),
    yaxis=dict(gridcolor=C_GRID, zerolinecolor=C_GRID),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(255,255,255,0.1)"),
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
Honeywell Campus Hackathon

Autonomous AI feedback loop:
- 🏢 EnergyPlus building sim
- 🧠 Ollama LLM (Qwen2.5-7B)
- 🔧 MCP Tool layer
- ♻️ Closed-loop control

**Target PMV:** -0.5 → +0.5
""")

    st.markdown("---")
    st.markdown("### 📁 Log Files")
    st.code(f"AI:       {LOG_FILE}\nBaseline: {BASELINE_LOG}")


# ──────────────────────────────────────────────
# HERO HEADER
# ──────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <div style="font-size:3rem">🏢</div>
  <div>
    <h1>Eco-Loop Building Agents</h1>
    <p>Honeywell Campus Hackathon · Autonomous AI-Driven HVAC Optimization · Real-time Dashboard</p>
  </div>
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
    <div class="metric-card">
      <div class="metric-value">{last.get('avg_zone_temp_c', '—')}°C</div>
      <div class="metric-label">Zone Temp</div>
      <div class="metric-sub">outdoor: {last.get('outdoor_temp_c', '—')}°C</div>
    </div>""", unsafe_allow_html=True)

with col2:
    pmv = last.get('pmv', 0)
    badge = "badge-ok" if PMV_MIN <= (pmv or 0) <= PMV_MAX else "badge-bad"
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-value">{pmv:+.2f}</div>
      <div class="metric-label">Current PMV</div>
      <div class="metric-sub {badge}">{last.get('comfort_ok') and 'Comfortable ✅' or 'Discomfort ⚠️'}</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-value">{ai_energy:.3f}</div>
      <div class="metric-label">Energy Used (kWh)</div>
      <div class="metric-sub">HVAC: {last.get('hvac_kw', '—')} kW</div>
    </div>""", unsafe_allow_html=True)

with col4:
    sv = f"{savings_pct}%" if savings_pct is not None else "Run baseline"
    sv_color = "#64ffda" if savings_pct and savings_pct > 0 else "#ffa726"
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-value" style="color:{sv_color}">{sv}</div>
      <div class="metric-label">Energy Savings</div>
      <div class="metric-sub">vs fixed setpoint</div>
    </div>""", unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-card">
      <div class="metric-value">{pmv_ok_pct}%</div>
      <div class="metric-label">Comfort Rate</div>
      <div class="metric-sub">timesteps in target</div>
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
        name="AI Zone Temp", line=dict(color=C_AI, width=2),
        fill="tozeroy", fillcolor="rgba(0,212,255,0.07)"
    ))
    fig.add_trace(go.Scatter(
        x=ai_df["timestep"], y=ai_df["outdoor_temp_c"],
        name="Outdoor Temp", line=dict(color="#ffa726", width=1.5, dash="dot")
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
        fillcolor="rgba(100,255,218,0.07)",
        line_width=0, annotation_text="Comfort Zone",
        annotation_position="top left",
        annotation_font_color=C_PMV_OK
    )
    fig2.add_trace(go.Scatter(
        x=ai_df["timestep"], y=ai_df["pmv"],
        name="AI PMV", line=dict(color=C_AI, width=2),
        mode="lines+markers",
        marker=dict(
            color=[C_PMV_OK if PMV_MIN <= v <= PMV_MAX else C_PMV_BAD
                   for v in ai_df["pmv"]],
            size=5
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
        name="AI Agent", line=dict(color=C_AI, width=2.5),
        fill="tozeroy", fillcolor="rgba(0,212,255,0.08)"
    ))
    if has_base and show_baseline:
        fig3.add_trace(go.Scatter(
            x=base_df["timestep"], y=base_df["energy_kwh"],
            name="Baseline (Fixed Setpoint)",
            line=dict(color=C_BASELINE, width=2.5, dash="dash"),
            fill="tozeroy", fillcolor="rgba(255,167,38,0.05)"
        ))
    fig3.update_layout(
        title="Cumulative Energy Consumption (kWh)",
        yaxis_title="kWh",
        **PLOT_LAYOUT
    )
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    fig4 = go.Figure()
    fig4.add_trace(go.Bar(
        x=ai_df["timestep"], y=ai_df["hvac_kw"],
        name="HVAC Power (kW)",
        marker_color=C_AI,
        marker_line_width=0,
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
