"""
llm_agent.py — Ollama LLM Agent for Eco-Loop Building Agents
Honeywell Campus Hackathon

The agent:
  1. Receives sensor data from MCP tools
  2. Builds a structured prompt describing the building state
  3. Asks the LLM what HVAC action to take
  4. Parses the LLM response to extract tool calls
  5. Executes those tool calls via mcp_tools.py
  6. Returns a decision record for logging
"""

import json
import re
import time
from typing import Optional

from config import (
    LLM_PROVIDER, OLLAMA_MODEL, OLLAMA_BASE_URL,
    GROQ_API_KEY, GROQ_MODEL,
    SETPOINT_MIN, SETPOINT_MAX, PMV_MIN, PMV_MAX, ZONES
)
from mcp_tools import call_tool

# ──────────────────────────────────────────────
# SYSTEM PROMPT
# ──────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are an autonomous building energy optimization agent.
Your goal is to minimize HVAC energy consumption while keeping occupants thermally comfortable.

COMFORT REQUIREMENT:
- PMV (Predicted Mean Vote) must stay between {PMV_MIN} and {PMV_MAX}
- PMV < {PMV_MIN} = too cold, PMV > {PMV_MAX} = too warm

HVAC CONTROL RULES:
- You can set zone temperature setpoints between {SETPOINT_MIN}°C and {SETPOINT_MAX}°C
- Higher setpoints in summer = more cooling energy = bad
- Lower setpoints in winter = more heating energy = bad
- Stay as close to the outdoor temperature as comfort allows

RESPONSE FORMAT (STRICTLY follow this):
You MUST respond with a JSON object only. No explanations outside the JSON.

{{
  "reasoning": "one sentence explaining your decision",
  "actions": [
    {{
      "tool": "set_hvac_setpoint",
      "args": {{
        "zone": "ZONE ONE",
        "temperature_celsius": 23.5
      }}
    }}
  ],
  "expected_pmv": 0.1,
  "energy_strategy": "brief note on energy saving approach"
}}

Available zones: {ZONES}
Available tools: set_hvac_setpoint, read_sensors, get_energy_usage, calculate_pmv
"""


# ──────────────────────────────────────────────
# USER PROMPT BUILDER
# ──────────────────────────────────────────────
def build_prompt(sensor_data: dict, pmv_data: dict) -> str:
    zone_info = []
    for zone, temp in sensor_data.get("zone_temps_c", {}).items():
        sp = sensor_data.get("setpoints_c", {}).get(zone, "?")
        zone_info.append(f"  - {zone}: temp={temp}°C, setpoint={sp}°C")

    zone_str = "\n".join(zone_info)
    pmv_val   = pmv_data.get("pmv", "unknown")
    ppd_val   = pmv_data.get("ppd_percent", "unknown")
    comfort   = pmv_data.get("comfort_status", "unknown")

    return f"""Current building state at timestep {sensor_data.get('timestep', '?')}:

OUTDOOR: {sensor_data.get('outdoor_temp_c', '?')}°C
TIME:    {sensor_data.get('hour', '?')}:00

ZONES:
{zone_str}

COMFORT:
  PMV = {pmv_val} ({comfort})
  PPD = {ppd_val}% dissatisfied

ENERGY:
  Total used: {sensor_data.get('total_energy_kwh', '?')} kWh
  HVAC power: {sensor_data.get('hvac_power_kw', '?')} kW

Decide the optimal HVAC setpoints to minimize energy while keeping comfort within target.
Respond ONLY with the JSON format specified in your system instructions."""


# ──────────────────────────────────────────────
# LLM CALLER
# ──────────────────────────────────────────────
def call_ollama(prompt: str) -> str:
    """Call local Ollama LLM and return the response text."""
    try:
        import ollama
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system",    "content": SYSTEM_PROMPT},
                {"role": "user",      "content": prompt},
            ],
            options={"temperature": 0.1, "num_predict": 512},
        )
        return response["message"]["content"]
    except Exception as e:
        print(f"[Ollama ERROR] {e}")
        return _fallback_response()


def call_groq(prompt: str) -> str:
    """Call Groq API (online fallback)."""
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.1,
            max_tokens=512,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[Groq ERROR] {e}")
        return _fallback_response()


def _fallback_response() -> str:
    """Rule-based fallback if LLM is unavailable."""
    import json
    print("[Agent] LLM unavailable — using rule-based fallback.")
    return json.dumps({
        "reasoning": "LLM unavailable. Using rule-based conservative setpoint.",
        "actions": [
            {
                "tool": "set_hvac_setpoint",
                "args": {"zone": ZONES[0], "temperature_celsius": 24.0}
            }
        ],
        "expected_pmv": 0.0,
        "energy_strategy": "fallback: conservative 24°C setpoint",
    })


# ──────────────────────────────────────────────
# RESPONSE PARSER
# ──────────────────────────────────────────────
def parse_llm_response(raw: str) -> Optional[dict]:
    """Extract and validate JSON from LLM response."""
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("```").strip()

    # Try to find JSON object in the response
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        print(f"[Parser] No JSON found in LLM response:\n{raw[:200]}")
        return None

    try:
        data = json.loads(match.group())
        # Validate required fields
        if "actions" not in data:
            print("[Parser] Missing 'actions' key in LLM response.")
            return None
        return data
    except json.JSONDecodeError as e:
        print(f"[Parser] JSON decode error: {e}\nRaw: {raw[:200]}")
        return None


# ──────────────────────────────────────────────
# MAIN AGENT STEP
# ──────────────────────────────────────────────
def agent_step(sensor_data: dict) -> dict:
    """
    One complete sense→think→act cycle.
    Returns a decision record dict for logging.
    """
    t0 = time.time()

    # 1. Calculate PMV for current conditions
    zone_temp = list(sensor_data.get("zone_temps_c", {}).values())
    avg_zone_temp = sum(zone_temp) / len(zone_temp) if zone_temp else 22.0

    pmv_data = call_tool("calculate_pmv", {
        "air_temp_c": avg_zone_temp,
        "relative_humidity": 50.0,
    })

    # 2. Build prompt and call LLM
    prompt   = build_prompt(sensor_data, pmv_data)
    raw_resp = call_ollama(prompt) if LLM_PROVIDER == "ollama" else call_groq(prompt)

    # 3. Parse response
    parsed = parse_llm_response(raw_resp)
    if parsed is None:
        print("[Agent] Failed to parse LLM response. Skipping this step.")
        return {
            "timestep": sensor_data.get("timestep"),
            "status":   "parse_error",
            "pmv":      pmv_data.get("pmv"),
            "energy_kwh": sensor_data.get("total_energy_kwh"),
            "latency_ms": round((time.time() - t0) * 1000),
        }

    # 4. Execute actions
    results = []
    for action in parsed.get("actions", []):
        tool_name = action.get("tool")
        tool_args  = action.get("args", {})
        try:
            result = call_tool(tool_name, tool_args)
            results.append({"tool": tool_name, "args": tool_args, "result": result})
            print(f"  [Action] {tool_name}({tool_args}) -> {result}")
        except Exception as e:
            print(f"  [Action ERROR] {tool_name}: {e}")
            results.append({"tool": tool_name, "error": str(e)})

    latency = round((time.time() - t0) * 1000)
    print(f"  [Agent] Reasoning: {parsed.get('reasoning', '')}")
    print(f"  [Agent] Strategy:  {parsed.get('energy_strategy', '')}")
    print(f"  [Agent] Latency:   {latency}ms")

    return {
        "timestep":        sensor_data.get("timestep"),
        "hour":            sensor_data.get("hour"),
        "outdoor_temp_c":  sensor_data.get("outdoor_temp_c"),
        "avg_zone_temp_c": round(avg_zone_temp, 2),
        "pmv":             pmv_data.get("pmv"),
        "ppd_percent":     pmv_data.get("ppd_percent"),
        "comfort_ok":      pmv_data.get("within_target"),
        "energy_kwh":      sensor_data.get("total_energy_kwh"),
        "hvac_kw":         sensor_data.get("hvac_power_kw"),
        "actions_taken":   results,
        "reasoning":       parsed.get("reasoning", ""),
        "energy_strategy": parsed.get("energy_strategy", ""),
        "expected_pmv":    parsed.get("expected_pmv"),
        "latency_ms":      latency,
        "status":          "ok",
    }
