import json
import random
import os

SCENARIOS = [
    # (zone_temp, pmv, energy_kwh, time, occupancy) → expected_action
    {"input_temp": 27.5, "pmv": 0.9, "energy": 45, "time": "14:00", "occ": "occupied",
     "action": "set_hvac_setpoints(zone='ZONE1', cooling_setpoint=22.0, heating_setpoint=20.0)",
     "reason": "PMV=0.9 exceeds comfort threshold +0.5. Zone too hot. Lower cooling setpoint urgently."},
    
    {"input_temp": 18.5, "pmv": -0.8, "energy": 55, "time": "08:00", "occ": "occupied",
     "action": "set_hvac_setpoints(zone='ZONE1', cooling_setpoint=24.0, heating_setpoint=22.0)",
     "reason": "PMV=-0.8 below comfort threshold -0.5. Zone too cold. Raise heating setpoint."},
    
    {"input_temp": 23.0, "pmv": 0.1, "energy": 70, "time": "22:00", "occ": "unoccupied",
     "action": "apply_ecm(ecm_name='setback_scheduling', parameters='{\"setback_temp\": 28, \"duration_hours\": 8}')",
     "reason": "Building unoccupied at night. Energy=70kWh is high. Apply setback scheduling to cut energy."},
    
    {"input_temp": 25.0, "pmv": 0.4, "energy": 80, "time": "13:00", "occ": "peak_hours",
     "action": "apply_ecm(ecm_name='load_shifting', parameters='{\"shift_hours\": 2}')",
     "reason": "Peak demand period. Comfort acceptable. Shift non-critical loads to reduce peak demand."},
    
    {"input_temp": 22.0, "pmv": -0.1, "energy": 30, "time": "06:00", "occ": "pre_occupancy",
     "action": "apply_ecm(ecm_name='pre_cooling', parameters='{\"target_temp\": 21, \"duration_hours\": 2}')",
     "reason": "Pre-occupancy hour. Pre-cool now using cheap off-peak energy to prepare for occupancy."},
]

def generate_dataset(n_samples=300, output_path="finetuning/hvac_dataset.jsonl"):
    """Generate synthetic HVAC control training data"""
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    samples = []
    
    for _ in range(n_samples):
        # Pick a base scenario and add noise
        base = random.choice(SCENARIOS)
        temp = base["input_temp"] + random.uniform(-1.5, 1.5)
        pmv = base["pmv"] + random.uniform(-0.1, 0.1)
        energy = base["energy"] + random.uniform(-10, 10)
        
        sample = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a building energy management AI. Optimize energy while maintaining PMV comfort between -0.5 and +0.5."
                },
                {
                    "role": "user", 
                    "content": f"Zone temperature: {temp:.1f}°C, PMV: {pmv:.2f}, Energy consumption: {energy:.0f}kWh, Time: {base['time']}, Occupancy: {base['occ']}. What control action should be taken?"
                },
                {
                    "role": "assistant",
                    "content": f"Analysis: {base['reason']}\n\nRecommended Action: {base['action']}"
                }
            ]
        }
        samples.append(sample)
    
    with open(output_path, "w") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")
    
    print(f"✅ Generated {n_samples} training samples -> {output_path}")
    return output_path

if __name__ == "__main__":
    generate_dataset(300)
