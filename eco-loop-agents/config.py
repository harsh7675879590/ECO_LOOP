import os

# Paths
BASE_DIR = r"C:\Users\harsh\OneDrive\Desktop\ECO\eco-loop-agents"
ENERGYPLUS_PATH = r"C:\EnergyPlusV23-2-0\energyplus.exe"
BASELINE_IDF = os.path.join(BASE_DIR, "building_models", "baseline.idf")

# We will use the default Chicago weather file that comes with EnergyPlus
WEATHER_FILE = r"C:\EnergyPlusV23-2-0\WeatherData\USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "simulation_logs")

# LLM Config
OLLAMA_MODEL = "qwen2.5:7b"           # Main agent
FINETUNED_MODEL = "qwen2.5:1.5b"      # Fine-tuned specialist

# Control Thresholds
PMV_MIN = -0.5
PMV_MAX = 0.5
TEMP_MIN_C = 20.0
TEMP_MAX_C = 26.0
COOLING_SP_DEFAULT = 24.0
HEATING_SP_DEFAULT = 21.0

# Simulation Parameters
TIMESTEP_MINUTES = 15
SIMULATION_HOURS = 24
