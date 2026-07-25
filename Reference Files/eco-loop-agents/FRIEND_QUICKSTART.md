# Eco-Loop Building Agents — Friend Quickstart Guide
### Honeywell Campus Hackathon | Autonomous HVAC Optimization

---

## Step 1 — Check Your Environment (30 seconds)

Open a terminal in this folder and run:

```bash
python setup_check.py
```

This tells you exactly what's installed and what's missing.

---

## Step 2 — Install Required Packages (2-3 minutes, one-time)

```bash
pip install -r requirements.txt
```

---

## Step 3 — Install the LLM (Ollama) — REQUIRED for full AI mode

> **Skip this if you just want to test with the rule-based fallback.** The demo works without Ollama.

1. Download Ollama: https://ollama.com/download (Windows installer, ~50 MB)
2. Install it, then open a terminal and run:
   ```bash
   ollama pull qwen2.5:7b
   ```
   This downloads the ~4.5 GB AI model. You only need to do this once.

> **Less than 8 GB RAM?** Use the smaller model instead:
> ```bash
> ollama pull qwen2.5:3b
> ```
> Then open `config.py` and change:
> ```python
> OLLAMA_MODEL = "qwen2.5:3b"
> ```

---

## Step 4 — Run the Full Demo (One command!)

```bash
python run_demo.py --timesteps 50
```

This automatically:
1. Clears old results
2. Runs the **baseline** (dumb fixed setpoint)
3. Runs the **AI agent** (smart dynamic setpoints)
4. Prints the energy savings comparison
5. Opens the **live dashboard** in your browser

---

## Manual Step-by-Step (if you prefer)

```bash
# Terminal 1 — Run baseline first
python baseline.py --timesteps 50 --interval 0

# Terminal 1 — Then run the AI agent
python main.py --timesteps 50 --interval 0

# Terminal 2 — Open the live dashboard
streamlit run dashboard.py
```

---

## Configuration (`config.py`)

| Setting | Default | Description |
|---|---|---|
| `MOCK_MODE` | `True` | `True` = no EnergyPlus needed (mock simulator). `False` = real EnergyPlus. |
| `LLM_PROVIDER` | `"ollama"` | `"ollama"` (offline) or `"groq"` (online, needs API key) |
| `OLLAMA_MODEL` | `"qwen2.5:7b"` | Change to `"qwen2.5:3b"` for low-RAM systems |
| `MAX_TIMESTEPS` | `50` | Number of sense-think-act cycles to run |

---

## Project Structure

```
eco-loop-agents/
├── run_demo.py        <- ONE-CLICK DEMO — start here
├── setup_check.py     <- Pre-flight environment checker
├── main.py            <- AI feedback loop
├── baseline.py        <- Fixed setpoint baseline run
├── dashboard.py       <- Streamlit live dashboard
├── llm_agent.py       <- Ollama/Groq LLM agent
├── mcp_tools.py       <- Sensor reading & HVAC control tools
├── energyplus_sim.py  <- EnergyPlus wrapper + mock simulator
├── config.py          <- All settings
└── requirements.txt   <- Python packages
```

---

## How It Works

```
CLOSED LOOP:

  Building sensors
       |
       v
  read_sensors() [MCP tool]
       |
       v
  LLM (Qwen2.5 via Ollama)
  "Outdoor=31C, Zone=24C, PMV=+0.3
   -> Set setpoint to 25.5C to save energy"
       |
       v
  set_hvac_setpoint() [MCP tool]
       |
       v
  EnergyPlus / Mock Simulator
       |
       `---> CSV log -> Dashboard
```

---

## What the Dashboard Shows

- **Energy Savings %** — AI vs Baseline cumulative kWh
- **PMV Comfort Index** — must stay between -0.5 and +0.5
- **Zone Temperature** vs outdoor temperature over time
- **AI Decision Log** — what the LLM decided each step and why

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ollama not found` | Install from https://ollama.com/download |
| `No space left on device` | Run `pip cache purge` to free several GB |
| LLM gives bad JSON | Already handled — auto-falls-back to rule-based |
| EnergyPlus not found | Keep `MOCK_MODE=True` in config.py (works perfectly for demo) |
| Unicode error on Windows | Run with `$env:PYTHONUTF8=1; python ...` or use `run_demo.py` |
