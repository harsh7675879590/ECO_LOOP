"""
energyplus_sim.py — EnergyPlus simulation wrapper
Honeywell Campus Hackathon — Eco-Loop Building Agents

Provides:
  - get_sensor_data()  → returns current building state dict
  - set_setpoint(zone, temp) → updates HVAC setpoint
  - get_energy_usage() → returns kWh consumed so far

Supports MOCK_MODE for testing without EnergyPlus installed.
"""

import os
import math
import random
import subprocess
import time
import csv
from datetime import datetime
from config import (
    MOCK_MODE, ENERGYPLUS_EXE, IDF_FILE, WEATHER_FILE,
    EP_OUTPUT_DIR, DEFAULT_SETPOINT, ZONES
)

# ──────────────────────────────────────────────
# MOCK SIMULATION (works without EnergyPlus)
# ──────────────────────────────────────────────
class MockSimulator:
    """Realistic building simulator for testing without EnergyPlus."""

    def __init__(self):
        self.timestep = 0
        self.zone_temps = {z: 22.0 for z in ZONES}
        self.setpoints  = {z: DEFAULT_SETPOINT for z in ZONES}
        self.total_kwh  = 0.0
        self.outdoor_temp = 30.0  # hot summer day default
        self._hour = 8  # start at 8 AM

    def step(self):
        """Advance simulation by one timestep (simulates 30 minutes)."""
        self.timestep += 1
        self._hour = (self._hour + 0.5) % 24

        # Outdoor temp varies sinusoidally over 24h (peaks at 2PM)
        self.outdoor_temp = 22 + 10 * math.sin(
            math.pi * (self._hour - 6) / 12
        ) + random.uniform(-1, 1)

        for zone in ZONES:
            sp = self.setpoints[zone]
            zt = self.zone_temps[zone]

            # Heat drift toward outdoor temp (thermal mass effect)
            drift = (self.outdoor_temp - zt) * 0.05
            # HVAC pulls toward setpoint
            hvac_pull = (sp - zt) * 0.3
            noise = random.uniform(-0.2, 0.2)

            self.zone_temps[zone] = round(zt + drift + hvac_pull + noise, 2)

            # Energy cost: higher when setpoint far from outdoor temp
            delta = abs(sp - self.outdoor_temp)
            kwh = (delta * 0.12 + 0.5) * 0.5   # per 30-min step
            self.total_kwh += round(kwh, 4)

    def get_sensor_data(self):
        self.step()
        return {
            "timestep": self.timestep,
            "hour":     round(self._hour, 1),
            "outdoor_temp_c":  round(self.outdoor_temp, 2),
            "zone_temps_c":    dict(self.zone_temps),
            "setpoints_c":     dict(self.setpoints),
            "total_energy_kwh": round(self.total_kwh, 4),
            "hvac_power_kw":   round(
                sum(abs(self.setpoints[z] - self.zone_temps[z]) * 0.5
                    for z in ZONES), 3
            ),
            "timestamp": datetime.now().isoformat(),
        }

    def set_setpoint(self, zone: str, temp: float):
        if zone in self.setpoints:
            self.setpoints[zone] = float(temp)

    def get_energy_usage(self):
        return round(self.total_kwh, 4)


# ──────────────────────────────────────────────
# REAL ENERGYPLUS SIMULATION
# ──────────────────────────────────────────────
class EnergyPlusSimulator:
    """
    Wraps EnergyPlus using its Python API (pyenergyplus).
    Falls back to subprocess + CSV output parsing if API unavailable.
    """

    def __init__(self):
        self.timestep = 0
        self.setpoints = {z: DEFAULT_SETPOINT for z in ZONES}
        self.total_kwh = 0.0
        self._sensor_cache = {}
        self._ep_api = None
        self._state   = None
        self._init_api()

    def _init_api(self):
        """Try to load pyenergyplus (bundled with EnergyPlus install)."""
        import sys
        ep_dir = os.path.dirname(ENERGYPLUS_EXE)
        if ep_dir not in sys.path:
            sys.path.insert(0, ep_dir)
        try:
            from pyenergyplus.api import EnergyPlusAPI
            self._ep_api = EnergyPlusAPI()
            self._state  = self._ep_api.state_manager.new_state()
            print("[EnergyPlus] Python API loaded successfully.")
        except ImportError:
            print("[EnergyPlus] API not found, using subprocess mode.")

    def _run_subprocess(self):
        """Run EnergyPlus as a subprocess and parse CSV output."""
        os.makedirs(EP_OUTPUT_DIR, exist_ok=True)
        cmd = [
            ENERGYPLUS_EXE,
            "-w", WEATHER_FILE,
            "-d", EP_OUTPUT_DIR,
            "-r",
            IDF_FILE,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"EnergyPlus failed:\n{result.stderr}")
        return self._parse_csv_output()

    def _parse_csv_output(self):
        """Parse EnergyPlus eplusout.csv for sensor values."""
        csv_path = os.path.join(EP_OUTPUT_DIR, "eplusout.csv")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"EnergyPlus output not found: {csv_path}")

        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            raise ValueError("EnergyPlus output CSV is empty.")

        last = rows[-1]
        zone_temps = {}
        for zone in ZONES:
            key = f"{zone}:Zone Mean Air Temperature [C](TimeStep)"
            zone_temps[zone] = float(last.get(key, DEFAULT_SETPOINT))

        total_kwh = 0.0
        energy_key = "EnergyTransferMeter:Facility [J](TimeStep)"
        if energy_key in last:
            total_kwh = float(last[energy_key]) / 3_600_000  # J → kWh

        outdoor_key = "Site Outdoor Air Drybulb Temperature [C](TimeStep)"
        outdoor_temp = float(last.get(outdoor_key, 25.0))

        return {
            "timestep": len(rows),
            "hour": len(rows) * 0.5 % 24,
            "outdoor_temp_c": round(outdoor_temp, 2),
            "zone_temps_c": zone_temps,
            "setpoints_c": dict(self.setpoints),
            "total_energy_kwh": round(total_kwh, 4),
            "hvac_power_kw": 0.0,
            "timestamp": datetime.now().isoformat(),
        }

    def get_sensor_data(self):
        self.timestep += 1
        try:
            data = self._run_subprocess()
            self._sensor_cache = data
            return data
        except Exception as e:
            print(f"[EnergyPlus WARNING] {e} — returning cached data.")
            return self._sensor_cache or {}

    def set_setpoint(self, zone: str, temp: float):
        self.setpoints[zone] = float(temp)
        # In a real integration, this would write back to the IDF
        # via eppy or the EnergyPlus runtime API actuators
        print(f"[EnergyPlus] Setpoint for '{zone}' -> {temp}C")

    def get_energy_usage(self):
        return self._sensor_cache.get("total_energy_kwh", 0.0)


# ──────────────────────────────────────────────
# FACTORY — pick the right simulator
# ──────────────────────────────────────────────
def get_simulator():
    if MOCK_MODE:
        print("[Simulator] MOCK_MODE=True — using built-in mock simulator.")
        print("            Set MOCK_MODE=False in config.py for real EnergyPlus.\n")
        return MockSimulator()
    else:
        print("[Simulator] MOCK_MODE=False — connecting to EnergyPlus...")
        return EnergyPlusSimulator()
