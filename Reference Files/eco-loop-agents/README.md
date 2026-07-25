# Eco-Loop Building Agents
### Honeywell Campus Hackathon — Autonomous AI-Driven HVAC Optimization

---

## 🚀 Quick Start (3 commands)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the AI agent loop (in Terminal 1)
python main.py

# 3. Open the live dashboard (in Terminal 2)
streamlit run dashboard.py
```

---

## 📋 Prerequisites

| Requirement | Status | Notes |
|---|---|---|
| Python 3.11+ | Required | https://python.org |
| Ollama | Required | https://ollama.com/download |
| qwen2.5:7b model | Required | `ollama pull qwen2.5:7b` |
| EnergyPlus 23.2.0 | Optional | For real simulation (not mock) |

---

## ⚙️ Configuration (`config.py`)

Open `config.py` and check these settings:

```python
# --- MOST IMPORTANT ---
MOCK_MODE = True       # True = test without EnergyPlus installed
                       # False = use real EnergyPlus simulation

LLM_PROVIDER = "ollama"      # "ollama" (offline) or "groq" (online)
OLLAMA_MODEL  = "qwen2.5:7b" # or "qwen2.5:3b" if RAM < 8GB
```

---

## 📁 Project Structure

```
eco-loop-agents/
├── main.py            # 🔄 Main feedback loop — run this first
├── baseline.py        # 📊 Baseline run (no AI, fixed setpoint)
├── dashboard.py       # 📺 Streamlit live dashboard
├── llm_agent.py       # 🧠 Ollama LLM agent
├── mcp_tools.py       # 🔧 MCP tool layer (sensors, control)
├── energyplus_sim.py  # ⚡ EnergyPlus wrapper + mock simulator
├── config.py          # ⚙️ All settings
└── requirements.txt
```

---

## 🎯 Demo Flow (for judges)

### Step 1 — Run baseline first
```bash
python baseline.py --timesteps 50
```
This records energy usage with a **fixed 22°C setpoint** (no intelligence).

### Step 2 — Run AI agent
```bash
python main.py --timesteps 50
```
The AI agent dynamically adjusts setpoints to save energy while maintaining comfort.

### Step 3 — Open dashboard
```bash
streamlit run dashboard.py
```
Shows side-by-side: **AI energy < Baseline energy**, PMV in target range.

---

## 🧠 How It Works

```
┌─────────────────────────────────────────────────────┐
│                  CLOSED LOOP                        │
│                                                     │
│  1. SENSE  →  read_sensors() via MCP                │
│       ↓                                             │
│  2. THINK  →  Qwen2.5-7B LLM decides setpoint       │
│       ↓       (locally via Ollama, no internet)     │
│  3. ACT    →  set_hvac_setpoint() via MCP            │
│       ↓                                             │
│  4. LOG    →  CSV → dashboard                       │
│       ↓                                             │
│  5. REPEAT every 2 seconds                          │
└─────────────────────────────────────────────────────┘
```

### MCP Tools Available to the LLM:
| Tool | Description |
|---|---|
| `read_sensors` | Zone temps, outdoor temp, HVAC power |
| `set_hvac_setpoint` | Change zone temperature target |
| `get_energy_usage` | Total kWh consumed |
| `calculate_pmv` | ISO 7730 thermal comfort index |

---

## 💡 CLI Options

```bash
# Run for exactly 100 timesteps
python main.py --timesteps 100

# Faster loop (1 second intervals)
python main.py --interval 1

# No LLM — rule-based only (for testing without Ollama)
python main.py --no-llm

# Baseline with custom setpoint
python baseline.py --setpoint 24.0 --timesteps 50
```

---

## 🔍 Troubleshooting

**"Connection refused" from Ollama:**
```bash
# Make sure Ollama is running
ollama serve
```

**"Model not found":**
```bash
ollama pull qwen2.5:7b
```

**Low RAM machine:**
```python
# In config.py, change:
OLLAMA_MODEL = "qwen2.5:3b"   # only 2GB download
```

**No EnergyPlus yet:**
```python
# In config.py:
MOCK_MODE = True   # already default — runs fine without EnergyPlus
```

**EnergyPlus installed but not working:**
- Verify path in config.py: `ENERGYPLUS_DIR = r"C:\EnergyPlusV23-2-0"`
- Check EnergyPlus version: must be 23.2.0

---

## 📊 Output Files

| File | Contents |
|---|---|
| `eco_loop_log.csv` | AI agent run — all timestep data |
| `baseline_results.csv` | Fixed setpoint baseline run |

Both files are read by `dashboard.py` for comparison charts.

---

## 🏆 Hackathon Scoring Alignment

| Criterion (weight) | How we address it |
|---|---|
| **Stable closed loop (30%)** | Crash-safe with fallback mock mode + rule-based backup |
| **Energy savings (25%)** | Proven by AI vs baseline CSV comparison on dashboard |
| **Thermal comfort PMV (20%)** | ISO 7730 calculation, LLM constrained to keep PMV ±0.5 |
| **MCP tool use (15%)** | All sensor reads + control via fastmcp tools |
| **Demo quality (10%)** | Live Streamlit dashboard with real-time charts |
