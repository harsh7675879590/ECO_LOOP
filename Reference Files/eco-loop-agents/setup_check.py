"""
setup_check.py — Pre-flight check for Eco-Loop Building Agents
Honeywell Campus Hackathon

Run this FIRST before anything else.
It tells you exactly what's ready and what's missing.

Usage:
    python setup_check.py
"""

import sys
import subprocess
import shutil
import os

# ─────────────────────────────────────────────────────
# ANSI colours (work on modern Windows Terminal / VS Code)
# ─────────────────────────────────────────────────────
GRN  = "\033[92m"
RED  = "\033[91m"
YLW  = "\033[93m"
BLU  = "\033[94m"
BOLD = "\033[1m"
RST  = "\033[0m"

OK   = f"{GRN}✔ OK{RST}"
FAIL = f"{RED}✘ MISSING{RST}"
WARN = f"{YLW}⚠ WARNING{RST}"

print(f"\n{BOLD}{'='*58}{RST}")
print(f"{BOLD}  ECO-LOOP BUILDING AGENTS — Setup Check{RST}")
print(f"{BOLD}{'='*58}{RST}\n")

issues = []

# ── 1. Python version ─────────────────────────────────
major, minor = sys.version_info.major, sys.version_info.minor
ver_str = f"Python {major}.{minor}.{sys.version_info.micro}"
if major == 3 and minor >= 10:
    print(f"  {OK}  {ver_str}")
else:
    print(f"  {FAIL}  {ver_str} (need Python 3.10+)")
    issues.append("Install Python 3.10+ from https://python.org")

# ── 2. Required packages ──────────────────────────────
packages = {
    "fastmcp":    "fastmcp",
    "streamlit":  "streamlit",
    "pandas":     "pandas",
    "plotly":     "plotly",
    "eppy":       "eppy",
    "ollama":     "ollama",
    "groq":       "groq",
}

print(f"\n  {BOLD}Python packages:{RST}")
for pkg, import_name in packages.items():
    try:
        __import__(import_name)
        print(f"    {OK}  {pkg}")
    except ImportError:
        print(f"    {FAIL}  {pkg}")
        issues.append(f"Run: pip install {pkg}")

# ── 3. Ollama executable ──────────────────────────────
print(f"\n  {BOLD}Ollama (LLM engine):{RST}")
ollama_path = shutil.which("ollama")
if ollama_path:
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True, text=True, timeout=5
        )
        version_line = result.stdout.strip() or result.stderr.strip()
        print(f"    {OK}  Ollama installed — {version_line}")
    except Exception:
        print(f"    {OK}  Ollama found at {ollama_path}")
else:
    print(f"    {FAIL}  Ollama not installed")
    issues.append(
        "Install Ollama: https://ollama.com/download\n"
        "         Then run: ollama pull qwen2.5:7b"
    )

# ── 4. Ollama model ───────────────────────────────────
print(f"\n  {BOLD}Ollama model (qwen2.5:7b):{RST}")
if ollama_path:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10
        )
        model_list = result.stdout
        if "qwen2.5:7b" in model_list:
            print(f"    {OK}  qwen2.5:7b is downloaded")
        elif "qwen2.5:3b" in model_list:
            print(f"    {WARN}  qwen2.5:3b found (3b works if RAM < 8GB)")
            print(f"           Edit config.py -> OLLAMA_MODEL = 'qwen2.5:3b'")
        else:
            print(f"    {FAIL}  Model not found")
            issues.append("Run: ollama pull qwen2.5:7b  (4.5 GB, needs internet once)")
    except Exception as e:
        print(f"    {WARN}  Could not list models: {e}")
else:
    print(f"    {WARN}  Skipped (Ollama not installed yet)")

# ── 5. EnergyPlus (optional) ──────────────────────────
print(f"\n  {BOLD}EnergyPlus (optional — mock mode works without it):{RST}")
ep_exe = r"C:\EnergyPlusV23-2-0\energyplus.exe"
if os.path.exists(ep_exe):
    print(f"    {OK}  EnergyPlus found at {ep_exe}")
    print(f"           Set MOCK_MODE=False in config.py to use real simulation")
else:
    print(f"    {WARN}  Not installed — MOCK_MODE=True will be used (perfectly fine for demo)")

# ── 6. Disk space ─────────────────────────────────────
print(f"\n  {BOLD}Disk space:{RST}")
try:
    import shutil as sh
    total, used, free = sh.disk_usage("C:\\")
    free_gb = free / (1024**3)
    if free_gb >= 2:
        print(f"    {OK}  {free_gb:.1f} GB free on C:\\")
    elif free_gb >= 0.5:
        print(f"    {WARN}  Only {free_gb:.1f} GB free — may be tight")
    else:
        print(f"    {FAIL}  Only {free_gb:.2f} GB free — free up space first!")
        issues.append("Free at least 2 GB on C:\\ before running")
except Exception:
    print(f"    {WARN}  Could not check disk space")

# ── Summary ───────────────────────────────────────────
print(f"\n{BOLD}{'='*58}{RST}")
if not issues:
    print(f"{GRN}{BOLD}  ✔ All checks passed! You're ready to run.{RST}")
    print(f"\n  {BOLD}Next steps:{RST}")
    print(f"    1.  python baseline.py --timesteps 50")
    print(f"    2.  python main.py --timesteps 50")
    print(f"    3.  streamlit run dashboard.py")
else:
    print(f"{YLW}{BOLD}  ⚠ Fix the following before running:{RST}")
    for i, issue in enumerate(issues, 1):
        print(f"\n  {i}. {issue}")

print(f"{BOLD}{'='*58}{RST}\n")
