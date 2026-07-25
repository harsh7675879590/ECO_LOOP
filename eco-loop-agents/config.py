"""
config.py — Central configuration for Eco-Loop Building Agents
Honeywell Campus Hackathon

Edit this file to match your friend's machine setup.
"""

import os

# ──────────────────────────────────────────────
# MODE SELECTION
# ──────────────────────────────────────────────
# Set to True to run without EnergyPlus installed (uses realistic mock data)
# Set to False when EnergyPlus is installed and you want the real simulation
MOCK_MODE = True  # <-- Keep this True for the real-time Dashboard Demo

# ──────────────────────────────────────────────
# LLM SETTINGS
# ──────────────────────────────────────────────
LLM_PROVIDER = "ollama"         # "ollama" (offline) or "groq" (online)
OLLAMA_MODEL  = "qwen2.5:7b"   # change to "qwen2.5:3b" if RAM < 8GB
OLLAMA_BASE_URL = "http://localhost:11434"

# Groq settings (only needed if LLM_PROVIDER = "groq")
GROQ_API_KEY  = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL    = "llama-3.1-8b-instant"

# ──────────────────────────────────────────────
# ENERGYPLUS SETTINGS
# ──────────────────────────────────────────────
ENERGYPLUS_DIR = r"C:\EnergyPlusV23-2-0"
ENERGYPLUS_EXE = os.path.join(ENERGYPLUS_DIR, "energyplus.exe")

# Path to the example IDF file (comes with EnergyPlus install)
IDF_FILE = os.path.join(
    ENERGYPLUS_DIR,
    "ExampleFiles",
    "1ZoneUncontrolled.idf"
)
WEATHER_FILE = os.path.join(
    ENERGYPLUS_DIR,
    "WeatherData",
    "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
)
EP_OUTPUT_DIR = "ep_output"

# ──────────────────────────────────────────────
# BUILDING / COMFORT SETTINGS
# ──────────────────────────────────────────────
# Thermal comfort: PMV must stay in [-0.5, +0.5]
PMV_MIN = -0.5
PMV_MAX =  0.5

# Allowed HVAC setpoint range (°C)
SETPOINT_MIN = 18.0
SETPOINT_MAX = 26.0
DEFAULT_SETPOINT = 22.0

# Zones to control (must match IDF zone names)
ZONES = ["ZONE ONE"]

# ──────────────────────────────────────────────
# LOOP SETTINGS
# ──────────────────────────────────────────────
LOOP_INTERVAL_SECONDS = 2      # delay between each sense→think→act cycle
MAX_TIMESTEPS = 50             # how many cycles to run (set to None for infinite)

# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────
LOG_FILE      = "eco_loop_log.csv"
BASELINE_LOG  = "baseline_results.csv"
