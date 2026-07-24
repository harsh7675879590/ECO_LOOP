import subprocess
import os
import shutil
import sys

# Add the project root to the path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ENERGYPLUS_PATH, BASELINE_IDF, WEATHER_FILE, OUTPUT_DIR

class EnergyPlusWrapper:
    def __init__(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self.idf_path = BASELINE_IDF
        
    def run_simulation(self, idf_path=None, output_prefix="run"):
        """Run a full EnergyPlus simulation and return output path"""
        idf = idf_path or self.idf_path
        out_dir = os.path.join(OUTPUT_DIR, output_prefix)
        os.makedirs(out_dir, exist_ok=True)
        
        if not os.path.exists(idf):
            raise FileNotFoundError(f"IDF file not found: {idf}")
            
        cmd = [
            ENERGYPLUS_PATH,
            "-w", WEATHER_FILE,
            "-d", out_dir,
            "-r",          # readvars to create csv
            idf
        ]
        print(f"Running EnergyPlus: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            raise RuntimeError(f"EnergyPlus failed: {result.stderr}\n{result.stdout}")
        return out_dir
    
    def run_baseline(self):
        """Run the unmodified baseline for comparison"""
        return self.run_simulation(output_prefix="baseline")

if __name__ == "__main__":
    wrapper = EnergyPlusWrapper()
    print("Testing baseline run...")
    try:
        out = wrapper.run_baseline()
        print(f"Success! Output saved to: {out}")
    except Exception as e:
        print(f"Error: {e}")
