"""
main.py — Eco-Loop Building Agents — Main Orchestrator
Honeywell Campus Hackathon

Runs the closed-loop:
  sense → think → act → log → repeat

Usage:
  python main.py
  python main.py --timesteps 100
  python main.py --no-llm   (rule-based only, no Ollama needed)
"""

import argparse
import csv
import os
import time
import signal
import sys
from datetime import datetime

from config import (
    LOOP_INTERVAL_SECONDS, MAX_TIMESTEPS, LOG_FILE, ZONES
)
from energyplus_sim import get_simulator
from mcp_tools import set_simulator
from llm_agent import agent_step

# ──────────────────────────────────────────────
# CLI ARGS
# ──────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Eco-Loop Building Agent")
parser.add_argument("--timesteps", type=int, default=MAX_TIMESTEPS,
                    help="Number of control timesteps to run")
parser.add_argument("--interval",  type=float, default=LOOP_INTERVAL_SECONDS,
                    help="Seconds between timesteps")
parser.add_argument("--no-llm",   action="store_true",
                    help="Run rule-based only (no Ollama)")
args = parser.parse_args()

# ──────────────────────────────────────────────
# CSV LOG SETUP
# ──────────────────────────────────────────────
LOG_FIELDS = [
    "timestep", "hour", "outdoor_temp_c", "avg_zone_temp_c",
    "pmv", "ppd_percent", "comfort_ok",
    "energy_kwh", "hvac_kw",
    "reasoning", "energy_strategy", "expected_pmv",
    "latency_ms", "status", "run_type"
]

def init_log():
    f   = open(LOG_FILE, "w", newline="")
    w   = csv.DictWriter(f, fieldnames=LOG_FIELDS, extrasaction="ignore")
    w.writeheader()
    return f, w

def log_step(writer, record: dict, run_type: str = "ai"):
    record["run_type"] = run_type
    writer.writerow(record)

# ──────────────────────────────────────────────
# RULE-BASED FALLBACK (no LLM)
# ──────────────────────────────────────────────
def rule_based_step(sensor_data: dict, sim) -> dict:
    """Simple rule: push setpoint toward outdoor temp with comfort guard."""
    from mcp_tools import call_tool
    outdoor = sensor_data.get("outdoor_temp_c", 25.0)
    zone_temps = sensor_data.get("zone_temps_c", {})
    avg_zone = sum(zone_temps.values()) / len(zone_temps) if zone_temps else 22.0

    pmv_data = call_tool("calculate_pmv", {"air_temp_c": avg_zone})
    pmv = pmv_data.get("pmv", 0)

    # Nudge setpoint toward outdoor temp if comfortable, else correct
    current_sp = list(sensor_data.get("setpoints_c", {}).values())
    current_sp = current_sp[0] if current_sp else 22.0

    if pmv < -0.5:
        new_sp = min(current_sp + 1.0, 26.0)   # too cold → warm up
    elif pmv > 0.5:
        new_sp = max(current_sp - 1.0, 18.0)   # too hot  → cool down
    else:
        # Comfort OK → drift toward outdoor (save energy)
        delta = (outdoor - current_sp) * 0.1
        new_sp = round(max(18.0, min(26.0, current_sp + delta)), 1)

    for zone in ZONES:
        call_tool("set_hvac_setpoint", {"zone": zone, "temperature_celsius": new_sp})

    return {
        "timestep":        sensor_data.get("timestep"),
        "hour":            sensor_data.get("hour"),
        "outdoor_temp_c":  sensor_data.get("outdoor_temp_c"),
        "avg_zone_temp_c": round(avg_zone, 2),
        "pmv":             pmv_data.get("pmv"),
        "ppd_percent":     pmv_data.get("ppd_percent"),
        "comfort_ok":      pmv_data.get("within_target"),
        "energy_kwh":      sensor_data.get("total_energy_kwh"),
        "hvac_kw":         sensor_data.get("hvac_power_kw"),
        "reasoning":       f"Rule: setpoint -> {new_sp}C",
        "energy_strategy": "Drift toward outdoor temp within comfort bounds",
        "expected_pmv":    pmv,
        "latency_ms":      0,
        "status":          "ok",
    }

# ──────────────────────────────────────────────
# GRACEFUL SHUTDOWN
# ──────────────────────────────────────────────
_running = True

def _handle_sigint(sig, frame):
    global _running
    print("\n\n[Main] Ctrl+C detected — finishing current step then stopping...")
    _running = False

signal.signal(signal.SIGINT, _handle_sigint)

# ──────────────────────────────────────────────
# MAIN LOOP
# ──────────────────────────────────────────────
def main():
    global _running

    print("=" * 60)
    print("  ECO-LOOP BUILDING AGENTS")
    print("  Honeywell Campus Hackathon")
    print("=" * 60)
    print(f"  Mode:       {'RULE-BASED (--no-llm)' if args.no_llm else 'AI (Ollama)'}")
    print(f"  Timesteps:  {args.timesteps or 'inf'}")
    print(f"  Interval:   {args.interval}s")
    print(f"  Log file:   {LOG_FILE}")
    print("=" * 60)
    print()

    # Initialize
    sim = get_simulator()
    set_simulator(sim)

    log_file, log_writer = init_log()
    step = 0
    total_steps = args.timesteps

    print("[Main] Starting control loop. Press Ctrl+C to stop.\n")

    try:
        while _running:
            if total_steps and step >= total_steps:
                print(f"\n[Main] Reached {total_steps} timesteps. Done.")
                break

            step += 1
            print(f"\n" + "-"*50)
            print(f"  TIMESTEP {step} / {total_steps or 'inf'}  |  {datetime.now().strftime('%H:%M:%S')}")
            print("-"*50)

            # Sense
            sensor_data = sim.get_sensor_data()
            print(f"  Outdoor:  {sensor_data.get('outdoor_temp_c')}deg C")
            zone_str = ", ".join(
                f"{z}={t}deg C"
                for z, t in sensor_data.get("zone_temps_c", {}).items()
            )
            print(f"  Zones:    {zone_str}")
            print(f"  Energy:   {sensor_data.get('total_energy_kwh')} kWh")

            # Think & Act
            if args.no_llm:
                record = rule_based_step(sensor_data, sim)
                run_type = "rule"
            else:
                print("  Querying LLM agent...")
                record = agent_step(sensor_data)
                run_type = "ai"

            # Log
            log_step(log_writer, record, run_type)
            log_file.flush()

            # Status
            status_icon = "[OK]" if record.get("comfort_ok") else "[WARN]"
            print(f"\n  PMV:      {record.get('pmv')} {status_icon}")
            print(f"  Decision: {record.get('reasoning', 'N/A')}")

            time.sleep(args.interval)

    finally:
        log_file.close()
        print(f"\n[Main] Log saved -> {LOG_FILE}")
        print(f"[Main] Run 'streamlit run dashboard.py' to view results!")

if __name__ == "__main__":
    main()
