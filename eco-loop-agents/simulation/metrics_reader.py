import pandas as pd
import os
import glob
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MetricsReader:
    def __init__(self, output_dir):
        self.output_dir = output_dir
    
    def read_latest(self):
        """Read the latest eplusout.csv and return key metrics"""
        csv_files = glob.glob(os.path.join(self.output_dir, "**", "*.csv"), recursive=True)
        if not csv_files:
            return {}
        
        df = pd.read_csv(sorted(csv_files)[-1])
        
        metrics = {
            "timestamp": df.iloc[-1, 0] if len(df) > 0 else "N/A",
            "zone_temps": {},
            "total_energy_kwh": 0,
            "pmv": 0.1, # Default placeholder if PMV isn't in output
        }
        
        # Extract zone temperature columns
        temp_cols = [c for c in df.columns if "Zone Mean Air Temperature" in c]
        for col in temp_cols:
            zone_name = col.split(":")[0].strip()
            metrics["zone_temps"][zone_name] = float(df[col].iloc[-1])
        
        # Extract energy (Converting J to kWh)
        energy_cols = [c for c in df.columns if "Electricity" in c or "Energy" in c]
        if energy_cols:
            # Typical energy output in EnergyPlus is in Joules. 1 kWh = 3,600,000 J
            metrics["total_energy_kwh"] = float(df[energy_cols[0]].sum()) / 3_600_000  
        
        # Extract PMV if available
        pmv_cols = [c for c in df.columns if "PMV" in c or "Fanger" in c]
        if pmv_cols:
            metrics["pmv"] = float(df[pmv_cols[0]].iloc[-1])
        
        return metrics
    
    def get_total_energy(self):
        """Return total kWh consumed in this run"""
        m = self.read_latest()
        return m.get("total_energy_kwh", 0)
