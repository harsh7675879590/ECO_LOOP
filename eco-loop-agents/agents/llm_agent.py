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
            
            # Log the decision
            decision = {
                "timestep": timestep,
                "time": time_of_day,
                "reasoning": reply,
                "timestamp": time.time()
            }
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
