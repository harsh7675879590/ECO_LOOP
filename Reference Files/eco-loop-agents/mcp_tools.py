"""
mcp_tools.py — MCP Tool Layer for Eco-Loop Building Agents
Honeywell Campus Hackathon

Defines tools the LLM agent can call to interact with the building:
  - read_sensors       → get current building state
  - set_hvac_setpoint  → change zone temperature setpoint
  - get_energy_usage   → total kWh consumed
  - calculate_pmv      → compute thermal comfort index

These are registered as MCP tools via fastmcp.
"""

import math
from typing import Any
from fastmcp import FastMCP

from config import SETPOINT_MIN, SETPOINT_MAX, PMV_MIN, PMV_MAX

# The simulator instance is injected at runtime (set by main.py)
_simulator = None

def set_simulator(sim):
    """Inject the simulator instance into this module."""
    global _simulator
    _simulator = sim

# ──────────────────────────────────────────────
# Create MCP server
# ──────────────────────────────────────────────
mcp = FastMCP("EcoLoop Building Controller")


@mcp.tool()
def read_sensors() -> dict:
    """
    Read current building sensor data.
    Returns zone temperatures, outdoor temperature, HVAC power,
    total energy usage, and current timestep.
    """
    if _simulator is None:
        raise RuntimeError("Simulator not initialized. Call set_simulator() first.")
    return _simulator.get_sensor_data()


@mcp.tool()
def set_hvac_setpoint(zone: str, temperature_celsius: float) -> dict:
    """
    Set the HVAC temperature setpoint for a specific zone.

    Args:
        zone: Zone name (e.g., 'ZONE ONE')
        temperature_celsius: Target temperature in Celsius (18–26°C allowed)

    Returns:
        Result dict with success status and applied setpoint.
    """
    if _simulator is None:
        raise RuntimeError("Simulator not initialized.")

    # Clamp to safe range
    clamped = max(SETPOINT_MIN, min(SETPOINT_MAX, temperature_celsius))
    if clamped != temperature_celsius:
        print(f"[MCP] Setpoint {temperature_celsius}°C clamped to {clamped}°C")

    _simulator.set_setpoint(zone, clamped)
    return {
        "success": True,
        "zone": zone,
        "setpoint_applied_c": clamped,
        "requested_c": temperature_celsius,
        "clamped": clamped != temperature_celsius,
    }


@mcp.tool()
def get_energy_usage() -> dict:
    """
    Get cumulative energy consumption since simulation started.
    Returns total kWh used.
    """
    if _simulator is None:
        raise RuntimeError("Simulator not initialized.")
    kwh = _simulator.get_energy_usage()
    return {
        "total_energy_kwh": kwh,
        "note": "Cumulative since simulation start"
    }


@mcp.tool()
def calculate_pmv(
    air_temp_c: float,
    mean_radiant_temp_c: float = None,
    air_velocity_ms: float = 0.1,
    relative_humidity: float = 50.0,
    metabolic_rate: float = 1.2,
    clothing_insulation: float = 0.5,
) -> dict:
    """
    Calculate Predicted Mean Vote (PMV) thermal comfort index.
    PMV should be between -0.5 (slightly cool) and +0.5 (slightly warm).
    Range: -3 (very cold) to +3 (very hot).

    Args:
        air_temp_c: Air temperature in Celsius
        mean_radiant_temp_c: Mean radiant temperature (defaults to air_temp)
        air_velocity_ms: Air velocity in m/s (default 0.1)
        relative_humidity: Relative humidity % (default 50)
        metabolic_rate: Activity level in met (1.0=seated, 1.2=light work)
        clothing_insulation: Clothing in clo (0.5=light summer, 1.0=typical winter)

    Returns:
        dict with pmv value, ppd %, and comfort assessment.
    """
    if mean_radiant_temp_c is None:
        mean_radiant_temp_c = air_temp_c

    # ISO 7730 simplified PMV calculation
    ta  = air_temp_c
    tr  = mean_radiant_temp_c
    vel = air_velocity_ms
    rh  = relative_humidity
    met = metabolic_rate
    clo = clothing_insulation

    # Clothing surface temperature (iterative approximation)
    icl = 0.155 * clo
    m   = met * 58.15
    w   = 0.0  # external work (assume 0 for building occupants)
    mw  = m - w

    # Clothing area factor
    fcl = 1.05 + 0.645 * icl if icl > 0.078 else 1.0 + 1.29 * icl

    # Heat transfer coefficient
    hcf = 12.1 * math.sqrt(vel)
    taa = ta + 273.0
    tra = tr + 273.0

    # Iteratively solve for clothing surface temperature
    tcl = ta + (35.5 - ta) / (3.5 * (6.45 * icl + 0.1))
    for _ in range(100):
        tcla = tcl + 273.0
        hc   = max(hcf, 2.38 * abs(tcl - ta) ** 0.25)
        tcl_new = 35.7 - 0.028 * mw - icl * (
            3.96e-8 * fcl * (tcla**4 - tra**4) + fcl * hc * (tcl - ta)
        )
        if abs(tcl_new - tcl) < 0.001:
            break
        tcl = (tcl + tcl_new) / 2

    tcla = tcl + 273.0
    hc   = max(hcf, 2.38 * abs(tcl - ta) ** 0.25)

    # Heat loss components
    hl1 = 3.05e-3 * (5733 - 6.99 * mw - rh * 13.3 * math.exp(16.6536 - 4030.18 / (ta + 235)))
    hl2 = 0.42 * (mw - 58.15) if mw > 58.15 else 0.0
    hl3 = 1.7e-5 * m * (5867 - rh * 13.3 * math.exp(16.6536 - 4030.18 / (ta + 235)))
    hl4 = 0.0014 * m * (34 - ta)
    hl5 = 3.96e-8 * fcl * (tcla**4 - tra**4)
    hl6 = fcl * hc * (tcl - ta)

    ts = 0.303 * math.exp(-0.036 * m) + 0.028
    pmv = ts * (mw - hl1 - hl2 - hl3 - hl4 - hl5 - hl6)
    pmv = round(max(-3.0, min(3.0, pmv)), 3)

    # PPD (Predicted Percentage Dissatisfied)
    ppd = round(100 - 95 * math.exp(-0.03353 * pmv**4 - 0.2179 * pmv**2), 1)

    # Comfort assessment
    if PMV_MIN <= pmv <= PMV_MAX:
        comfort = "COMFORTABLE ✅"
    elif pmv < PMV_MIN:
        comfort = "TOO COOL ❄️"
    else:
        comfort = "TOO WARM 🔥"

    return {
        "pmv": pmv,
        "ppd_percent": ppd,
        "comfort_status": comfort,
        "within_target": PMV_MIN <= pmv <= PMV_MAX,
        "target_range": f"{PMV_MIN} to {PMV_MAX}",
    }


# ──────────────────────────────────────────────
# Convenience: call a tool by name (used by llm_agent)
# ──────────────────────────────────────────────
TOOL_REGISTRY = {
    "read_sensors":       read_sensors,
    "set_hvac_setpoint":  set_hvac_setpoint,
    "get_energy_usage":   get_energy_usage,
    "calculate_pmv":      calculate_pmv,
}

def call_tool(name: str, args: dict = None) -> Any:
    """Directly invoke a tool by name with args dict."""
    if name not in TOOL_REGISTRY:
        raise ValueError(f"Unknown tool: '{name}'. Available: {list(TOOL_REGISTRY.keys())}")
    fn = TOOL_REGISTRY[name]
    return fn(**(args or {}))
