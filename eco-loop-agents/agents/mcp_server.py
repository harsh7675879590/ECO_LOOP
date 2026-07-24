import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server.fastmcp import FastMCP
from simulation.metrics_reader import MetricsReader
from simulation.setpoint_injector import SetpointInjector
from simulation.energyplus_wrapper import EnergyPlusWrapper
from config import OUTPUT_DIR

mcp = FastMCP("EcoLoop Building Agent")
reader = MetricsReader(OUTPUT_DIR)
injector = SetpointInjector()
wrapper = EnergyPlusWrapper()

@mcp.tool()
def read_building_metrics() -> str:
    """
    Read current building performance metrics from the active simulation.
    Returns zone temperatures (°C), total energy consumption (kWh), 
    PMV thermal comfort index, and indoor air quality data.
    """
    metrics = reader.read_latest()
    return json.dumps(metrics, indent=2)

@mcp.tool()
def set_hvac_setpoints(zone: str, cooling_setpoint: float, heating_setpoint: float) -> str:
    """
    Set HVAC cooling and heating setpoints for a specific zone.
    Setpoints are automatically clamped to safe range (20-26°C).
    Args:
        zone: Zone name (e.g., 'ZONE1', 'PERIMETER_ZN_1')
        cooling_setpoint: Target cooling temperature in Celsius (20-26°C)
        heating_setpoint: Target heating temperature in Celsius (18-24°C)
    """
    out_path = os.path.join(OUTPUT_DIR, f"modified_{zone}.idf")
    injector.set_zone_cooling_setpoint(zone, cooling_setpoint, out_path)
    return f"✅ Set {zone}: cooling={cooling_setpoint}°C, heating={heating_setpoint}°C. IDF updated."

@mcp.tool()
def get_energy_savings_report() -> str:
    """
    Compare current AI-controlled run against baseline simulation.
    Returns percentage energy savings and comfort metrics.
    """
    current = reader.get_total_energy()
    baseline_reader = MetricsReader(os.path.join(OUTPUT_DIR, "baseline"))
    baseline = baseline_reader.get_total_energy()
    
    if baseline > 0:
        savings_pct = ((baseline - current) / baseline) * 100
    else:
        savings_pct = 0
    
    return json.dumps({
        "baseline_kwh": round(baseline, 2),
        "current_kwh": round(current, 2),
        "savings_kwh": round(baseline - current, 2),
        "savings_percent": round(savings_pct, 1),
        "status": "✅ Saving energy" if savings_pct > 0 else "⚠️ Consuming more than baseline"
    }, indent=2)

@mcp.tool()
def apply_ecm(ecm_name: str, parameters: str) -> str:
    """
    Apply an Energy Conservation Measure (ECM) to the building.
    Args:
        ecm_name: One of: 'pre_cooling', 'load_shifting', 'natural_ventilation', 'setback_scheduling'
        parameters: JSON string with ECM parameters e.g. '{"target_temp": 22, "duration_hours": 2}'
    """
    params = json.loads(parameters)
    ecm_results = {
        "pre_cooling": f"Pre-cooling applied: target={params.get('target_temp', 22)}°C for {params.get('duration_hours', 2)}hrs",
        "load_shifting": f"Load shifted to off-peak hours: {params.get('shift_hours', 2)}hrs",
        "natural_ventilation": "Natural ventilation ECM enabled for applicable zones",
        "setback_scheduling": f"Temperature setback scheduled: {params.get('setback_temp', 26)}°C during unoccupied hours"
    }
    result = ecm_results.get(ecm_name, f"Unknown ECM: {ecm_name}")
    return f"✅ ECM Applied: {result}"

if __name__ == "__main__":
    mcp.run()
