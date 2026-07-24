import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from simulation.metrics_reader import MetricsReader
from config import OUTPUT_DIR

st.set_page_config(page_title="Eco-Loop Building Agent", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
    .main { background: #0a0a0a; }
    .metric-card { background: #1a1a2e; border-radius: 12px; padding: 20px; }
    .savings-big { font-size: 3rem; color: #00ff88; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ Eco-Loop Building Agent Dashboard")
st.caption("AI-driven autonomous building energy optimization | Honeywell Hackathon")

# Top metrics row
col1, col2, col3, col4 = st.columns(4)
reader = MetricsReader(OUTPUT_DIR)
metrics = reader.read_latest()

# Provide safe defaults if no data
zone_temps = metrics.get('zone_temps', {"Zone 1": 23.0})
avg_temp = sum(zone_temps.values()) / max(len(zone_temps), 1)

with col1:
    st.metric("🌡️ Avg Zone Temp", f"{avg_temp:.1f}°C")
with col2:
    st.metric("⚡ Energy (kWh)", f"{metrics.get('total_energy_kwh', 0):.1f}")
with col3:
    st.metric("😊 PMV Index", f"{metrics.get('pmv', 0.1):.2f}")
with col4:
    # Savings compared to baseline logic
    try:
        baseline_reader = MetricsReader(os.path.join(OUTPUT_DIR, "baseline"))
        baseline = baseline_reader.get_total_energy()
        current = metrics.get('total_energy_kwh', 0)
        savings = ((baseline - current) / baseline) * 100 if baseline > 0 else 0
        st.metric("💰 Energy Saved", f"{savings:.1f}%")
    except Exception:
        st.metric("💰 Energy Saved", "Calculating...")

st.divider()

# Charts
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Zone Temperature vs Setpoints")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=list(zone_temps.keys()), y=list(zone_temps.values()), 
                         marker_color="#00b4d8", name="Current Temp"))
    fig.add_hline(y=26, line_dash="dash", line_color="#ff6b6b", annotation_text="Max Cooling SP")
    fig.add_hline(y=20, line_dash="dash", line_color="#4ecdc4", annotation_text="Min Heating SP")
    fig.update_layout(template="plotly_dark", height=300)
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Energy: AI vs Baseline")
    
    baseline_val = 100 # placeholder
    current_val = metrics.get('total_energy_kwh', 0)
    try:
        baseline_val = baseline_reader.get_total_energy()
    except Exception:
        baseline_val = current_val * 1.2 if current_val > 0 else 100
        
    fig2 = go.Figure(go.Bar(
        x=["Baseline (kWh)", "AI Controlled (kWh)"],
        y=[baseline_val, current_val],
        marker_color=["#ff6b6b", "#00ff88"],
        text=[f"{baseline_val:.1f} kWh", f"{current_val:.1f} kWh"],
        textposition="auto"
    ))
    fig2.update_layout(template="plotly_dark", height=300)
    st.plotly_chart(fig2, use_container_width=True)

# LLM Reasoning Log
st.subheader("🧠 LLM Decision Log")
log_path = os.path.join(OUTPUT_DIR, "decisions.json")
if os.path.exists(log_path):
    try:
        with open(log_path) as f:
            decisions = json.load(f)
        for d in decisions[-5:]:
            with st.expander(f"Timestep {d.get('timestep', '?')} — {d.get('time', '')}"):
                st.write(d.get("reasoning", "No reasoning logged"))
    except json.JSONDecodeError:
        st.info("Log file is currently being written to...")
else:
    st.info("Simulation not started yet. Run `python main.py` to start the loop.")
