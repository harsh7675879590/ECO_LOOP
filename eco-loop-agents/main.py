import os
import time
import json
from simulation.energyplus_wrapper import EnergyPlusWrapper
from simulation.metrics_reader import MetricsReader
from agents.llm_agent import LLMAgent
from config import OUTPUT_DIR, TIMESTEP_MINUTES, SIMULATION_HOURS

def get_occupancy(hour: int) -> str:
    if 8 <= hour <= 17:
        return "occupied (business hours)"
    elif 6 <= hour < 8:
        return "pre_occupancy"
    else:
        return "unoccupied"

def main():
    print("=" * 60)
    print("  ECO-LOOP BUILDING AGENT - Starting Control Pipeline")
    print("=" * 60)
    
    wrapper = EnergyPlusWrapper()
    agent = LLMAgent()
    
    # Step 1: Run baseline (for comparison)
    print("\n[1/4] Running baseline simulation...")
    try:
        baseline_dir = wrapper.run_baseline()
        print(f"✅ Baseline complete: {baseline_dir}")
    except Exception as e:
        print(f"⚠️ Baseline run failed (check if EnergyPlus path is correct): {e}")
        # Will continue anyway for the sake of the hackathon loop
    
    # Step 2: Run AI-controlled simulation
    print("\n[2/4] Starting AI-controlled simulation...")
    try:
        ai_run_dir = wrapper.run_simulation(output_prefix="ai_run")
        reader = MetricsReader(ai_run_dir)
    except Exception as e:
        print(f"⚠️ AI run setup failed: {e}")
        return
        
    # Step 3: Control Loop
    print("\n[3/4] Entering autonomous control loop...")
    decisions = []
    
    total_timesteps = (SIMULATION_HOURS * 60) // TIMESTEP_MINUTES
    
    # Pre-create decisions.json if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_path = os.path.join(OUTPUT_DIR, "decisions.json")
    with open(log_path, "w") as f:
        json.dump([], f)
    
    for ts in range(total_timesteps):
        hour = (ts * TIMESTEP_MINUTES // 60) % 24
        time_str = f"{hour:02d}:{(ts * TIMESTEP_MINUTES % 60):02d}"
        occupancy = get_occupancy(hour)
        
        print(f"\n[Timestep {ts+1}/{total_timesteps}] Time: {time_str} | Occupancy: {occupancy}")
        
        # LLM makes a decision
        decision = agent.decide(ts + 1, time_str, occupancy)
        decisions.append(decision)
        print(f"  🧠 LLM: {decision.get('reasoning', 'No reasoning generated')[:150]}...")
        
        # Save decision log for dashboard
        try:
            with open(log_path, "w") as f:
                json.dump(decisions, f, indent=2)
        except Exception as e:
            pass
        
        # Pause to simulate real-time loop / avoid API spamming
        time.sleep(1)
    
    # Step 4: Final report
    print("\n[4/4] Generating savings report...")
    try:
        baseline_reader = MetricsReader(os.path.join(OUTPUT_DIR, "baseline"))
        ai_reader = MetricsReader(os.path.join(OUTPUT_DIR, "ai_run"))
        
        baseline_kwh = baseline_reader.get_total_energy()
        ai_kwh = ai_reader.get_total_energy()
        savings = ((baseline_kwh - ai_kwh) / max(baseline_kwh, 1)) * 100
        
        print(f"\n{'='*60}")
        print(f"  FINAL RESULTS")
        print(f"  Baseline:     {baseline_kwh:.2f} kWh")
        print(f"  AI-Controlled: {ai_kwh:.2f} kWh")
        print(f"  Savings:       {savings:.1f}%")
        print(f"{'='*60}")
    except Exception as e:
        print(f"Could not generate final report: {e}")

if __name__ == "__main__":
    main()
