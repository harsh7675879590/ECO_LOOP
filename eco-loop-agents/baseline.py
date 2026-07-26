"""
baseline.py — Run EnergyPlus with fixed default setpoints (no AI)
Honeywell Campus Hackathon — Eco-Loop Building Agents

Runs the same number of timesteps as main.py but with a fixed
setpoint to establish the baseline energy usage for comparison.

Usage:
  python baseline.py
  python baseline.py --timesteps 50 --setpoint 22.0
"""

import argparse
import csv
import os
import time
import signal

from config import (
    LOOP_INTERVAL_SECONDS, MAX_TIMESTEPS,
    BASELINE_LOG, DEFAULT_SETPOINT, ZONES
)
from energyplus_sim import get_simulator
from mcp_tools import set_simulator, call_tool

parser = argparse.ArgumentParser(description="Eco-Loop Baseline Runner")
parser.add_argument("--timesteps", type=int, default=MAX_TIMESTEPS)
parser.add_argument("--setpoint",  type=float, default=DEFAULT_SETPOINT,
                    help="Fixed setpoint temperature (°C)")
parser.add_argument("--interval",  type=float, default=LOOP_INTERVAL_SECONDS)
args = parser.parse_args()

LOG_FIELDS = [
    "timestep", "hour", "outdoor_temp_c", "avg_zone_temp_c",
    "pmv", "ppd_percent", "energy_kwh", "hvac_kw", "run_type"
]

_running = True

def _handle_sigint(sig, frame):
    global _running
    print("\n[Baseline] Stopping...")
    _running = False

signal.signal(signal.SIGINT, _handle_sigint)


def main():
    global _running

    print("=" * 60)
    print("  ECO-LOOP — BASELINE RUN")
    print(f"  Fixed setpoint: {args.setpoint}°C for all zones")
    print(f"  Timesteps:      {args.timesteps}")
    print(f"  Log file:       {BASELINE_LOG}")
    print("=" * 60)

    sim = get_simulator()
    set_simulator(sim)

    # Set fixed setpoint
    for zone in ZONES:
        sim.set_setpoint(zone, args.setpoint)

    log_f = open(BASELINE_LOG, "w", newline="")
    writer = csv.DictWriter(log_f, fieldnames=LOG_FIELDS, extrasaction="ignore")
    writer.writeheader()

    step = 0
    try:
        while _running:
            if args.timesteps and step >= args.timesteps:
                break

            step += 1
            sensor = sim.get_sensor_data()

            zone_temps = list(sensor.get("zone_temps_c", {}).values())
            avg_temp = sum(zone_temps) / len(zone_temps) if zone_temps else 22.0

            pmv_data = call_tool("calculate_pmv", {"air_temp_c": avg_temp})

            record = {
                "timestep":        sensor.get("timestep"),
                "hour":            sensor.get("hour"),
                "outdoor_temp_c":  sensor.get("outdoor_temp_c"),
                "avg_zone_temp_c": round(avg_temp, 2),
                "pmv":             pmv_data.get("pmv"),
                "ppd_percent":     pmv_data.get("ppd_percent"),
                "energy_kwh":      sensor.get("total_energy_kwh"),
                "hvac_kw":         sensor.get("hvac_power_kw"),
                "run_type":        "baseline",
            }
            writer.writerow(record)
            log_f.flush()

            print(
                f"  Step {step:3d} | "
                f"Zone={avg_temp:.1f}°C | "
                f"PMV={record['pmv']:+.2f} | "
                f"Energy={record['energy_kwh']:.3f} kWh"
            )
            time.sleep(args.interval)

    finally:
        log_f.close()
        print(f"\n[Baseline] Done! Results saved -> {BASELINE_LOG}")
        print("[Baseline] Run 'streamlit run dashboard.py' to compare vs AI run!")

if __name__ == "__main__":
    main()
