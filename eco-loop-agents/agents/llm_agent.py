import ollama
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.prompts import SYSTEM_PROMPT, CONTROL_PROMPT_TEMPLATE
from config import OLLAMA_MODEL

class LLMAgent:
    def __init__(self, model=OLLAMA_MODEL):
        self.model = model
        self.conversation_history = []
        self.decision_log = []
        
    def decide(self, timestep: int, time_of_day: str, occupancy: str) -> dict:
        """Run one control cycle — LLM reasons and takes actions"""
        user_msg = CONTROL_PROMPT_TEMPLATE.format(
            timestep=timestep,
            time_of_day=time_of_day,
            occupancy=occupancy
        )
        
        self.conversation_history.append({
            "role": "user",
            "content": user_msg
        })
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *self.conversation_history
                ],
                options={"temperature": 0.3, "num_predict": 512}
            )
            
            reply = response["message"]["content"]
            self.conversation_history.append({
                "role": "assistant", 
                "content": reply
            })
            
            # Log the decision with structured fields extracted from reasoning
            decision = {
                "timestep": timestep,
                "time": time_of_day,
                "reasoning": reply,
                "timestamp": time.time(),
                "occupancy": occupancy,
            }

            # Extract setpoints from reasoning text using heuristics
            import re
            from config import COOLING_SP_DEFAULT, HEATING_SP_DEFAULT

            cool_sp = COOLING_SP_DEFAULT
            heat_sp = HEATING_SP_DEFAULT

            # Look for explicit setpoint numbers mentioned in the text
            cool_match = re.search(r"cooling.{0,30}?(\d{2}(?:\.\d)?)\s*[°℃]?C", reply, re.IGNORECASE)
            heat_match = re.search(r"heating.{0,30}?(\d{2}(?:\.\d)?)\s*[°℃]?C", reply, re.IGNORECASE)
            if cool_match:
                val = float(cool_match.group(1))
                if 18 <= val <= 32:
                    cool_sp = val
            if heat_match:
                val = float(heat_match.group(1))
                if 14 <= val <= 28:
                    heat_sp = val

            # Apply sensible defaults based on occupancy if LLM mentioned setback/energy-saving
            setback_keywords = ["setback", "unoccupied", "reduce", "energy-saving", "off-peak", "load shift", "pre-cool"]
            if any(kw in reply.lower() for kw in setback_keywords) and occupancy != "occupied":
                cool_sp = max(cool_sp, COOLING_SP_DEFAULT + 2)   # raise cooling SP to save energy
                heat_sp = min(heat_sp, HEATING_SP_DEFAULT - 2)   # lower heating SP to save energy

            decision["cooling_setpoint"] = cool_sp
            decision["heating_setpoint"] = heat_sp

            # Detect ECM mentions
            if "pre_cool" in reply.lower() or "pre-cool" in reply.lower():
                decision["ecm"] = "pre_cooling"
            elif "load_shift" in reply.lower() or "load shift" in reply.lower():
                decision["ecm"] = "load_shift"
            elif "demand_response" in reply.lower() or "demand response" in reply.lower():
                decision["ecm"] = "demand_response"
            elif "setback" in reply.lower():
                decision["ecm"] = "setback_scheduling"

            self.decision_log.append(decision)
            
            # Keep conversation manageable (last 10 turns)
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return decision
            
        except Exception as e:
            return {
                "timestep": timestep,
                "reasoning": f"LLM error: {e}. Using fallback rule-based control.",
                "fallback": True
            }
    
    def get_decision_log(self):
        return self.decision_log
