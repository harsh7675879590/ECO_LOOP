"""
run_demo.py — One-click demo launcher for Eco-Loop Building Agents
Honeywell Campus Hackathon

This script:
  1. Clears previous log files
  2. Runs baseline (fixed 22C setpoint, no AI)
  3. Runs AI agent (rule-based mode if Ollama not installed, LLM mode if it is)
  4. Opens Streamlit dashboard in your browser automatically

Usage:
    python run_demo.py
    python run_demo.py --timesteps 100
    python run_demo.py --force-rule-based
"""

import argparse
import os
import sys
import subprocess
import time

# ─────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Eco-Loop Demo Runner")
parser.add_argument("--timesteps", type=int, default=50,
                    help="Number of control cycles to run (default: 50)")
parser.add_argument("--force-rule-based", action="store_true",
                    help="Skip Ollama check and use rule-based agent")
args = parser.parse_args()

SEP = "=" * 60

def banner(msg):
    print(f"\n{SEP}")
    print(f"  {msg}")
    print(SEP)

def step(num, msg):
    print(f"\n  [{num}] {msg}")

def run(cmd, description):
    """Run a python command with UTF-8 output enabled."""
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    print(f"\n  Running: {' '.join(cmd)}\n")
    result = subprocess.run(
        cmd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print(f"\n  [ERROR] {description} exited with code {result.returncode}")
        sys.exit(1)

# ─────────────────────────────────────────────────────
# CHECK OLLAMA
# ─────────────────────────────────────────────────────
def check_ollama():
    """Returns True if Ollama is available and model is pulled."""
    if args.force_rule_based:
        return False
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=5
        )
        if "qwen2.5" in result.stdout:
            return True
        print("  [INFO] Ollama found but no qwen2.5 model. Using rule-based mode.")
        return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

# ─────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────
banner("ECO-LOOP BUILDING AGENTS — DEMO LAUNCHER")
print(f"  Timesteps:   {args.timesteps}")

# Step 0 — Clear old log files
step(0, "Clearing previous run logs...")
for f in ["eco_loop_log.csv", "baseline_results.csv"]:
    if os.path.exists(f):
        os.remove(f)
        print(f"     Removed {f}")
print("  Done.")

# Step 1 — Baseline
step(1, "Running BASELINE (fixed 22C setpoint, no AI)...")
run(
    [sys.executable, "baseline.py", "--timesteps", str(args.timesteps), "--interval", "0"],
    "Baseline runner"
)

# Step 2 — AI Agent
use_llm = check_ollama()
if use_llm:
    step(2, "Running AI AGENT (Ollama LLM mode)...")
    cmd = [sys.executable, "main.py", "--timesteps", str(args.timesteps), "--interval", "0"]
else:
    step(2, "Running AI AGENT (rule-based mode — Ollama not detected)...")
    cmd = [sys.executable, "main.py", "--timesteps", str(args.timesteps), "--interval", "0", "--no-llm"]

run(cmd, "Main agent")

# Step 3 — Results summary
step(3, "Results summary:")
try:
    import pandas as pd
    baseline_df = pd.read_csv("baseline_results.csv")
    ai_df       = pd.read_csv("eco_loop_log.csv")

    b_steps  = len(baseline_df)
    a_steps  = len(ai_df)

    # Normalize to per-step averages so unequal run lengths compare fairly
    b_energy_per_step = baseline_df["energy_kwh"].max() / b_steps if b_steps > 0 else 0
    a_energy_per_step = ai_df["energy_kwh"].max()       / a_steps if a_steps > 0 else 0

    b_energy = b_energy_per_step * b_steps   # raw totals (for display)
    a_energy = a_energy_per_step * a_steps

    savings  = ((b_energy_per_step - a_energy_per_step) / b_energy_per_step * 100) if b_energy_per_step > 0 else 0

    b_comfort = baseline_df["pmv"].between(-0.5, 0.5).mean() * 100
    a_comfort = ai_df["pmv"].between(-0.5, 0.5).mean() * 100

    print(f"\n     {'Metric':<25} {'Baseline':>12} {'AI Agent':>12} {'Delta':>10}")
    print(f"     {'-'*60}")
    print(f"     {'Steps run':<25} {b_steps:>12} {a_steps:>12}")
    print(f"     {'Energy/step (kWh)':<25} {b_energy_per_step:>12.4f} {a_energy_per_step:>12.4f} {a_energy_per_step-b_energy_per_step:>+10.4f}")
    print(f"     {'Energy Savings':<25} {'':<12} {'':<12} {savings:>+9.1f}%")
    print(f"     {'PMV Comfort %':<25} {b_comfort:>11.1f}% {a_comfort:>11.1f}%")
    print()
except Exception as e:
    print(f"     Could not load results: {e}")

# Step 4 — Dashboard
step(4, "Launching Streamlit dashboard...")
print("     Dashboard will open in your browser automatically.")
print("     Press Ctrl+C in this terminal to stop the dashboard.\n")
time.sleep(1)

env = os.environ.copy()
env["PYTHONUTF8"] = "1"
subprocess.run(
    [sys.executable, "-m", "streamlit", "run", "dashboard.py"],
    env=env,
)
