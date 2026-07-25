import pandas as pd
import os
import glob
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MetricsReader:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def _read_meter_csv(self):
        """Read eplusmtr.csv which contains energy consumption data"""
        path = os.path.join(self.output_dir, "eplusmtr.csv")
        if os.path.exists(path):
            return pd.read_csv(path)
        return None

    def _read_output_csv(self):
        """Read eplusout.csv which contains zone temperature data"""
        path = os.path.join(self.output_dir, "eplusout.csv")
        if os.path.exists(path):
            return pd.read_csv(path)
        return None

    def read_latest(self):
        """Read metrics and return a dict with key building performance values"""
        metrics = {
            "timestamp": "N/A",
            "zone_temps": {},
            "total_energy_kwh": 0,
            "pmv": 0.1,
        }

        # Get zone temperatures from eplusout.csv
        df_out = self._read_output_csv()
        if df_out is not None and len(df_out) > 0:
            metrics["timestamp"] = df_out.iloc[-1, 0]
            temp_cols = [c for c in df_out.columns if "Zone Air Temperature" in c]
            for col in temp_cols:
                zone_name = col.split(":")[0].strip()
                try:
                    metrics["zone_temps"][zone_name] = float(df_out[col].iloc[-1])
                except (ValueError, TypeError):
                    pass
            # PMV if available
            pmv_cols = [c for c in df_out.columns if "PMV" in c or "Fanger" in c]
            if pmv_cols:
                try:
                    metrics["pmv"] = float(df_out[pmv_cols[0]].iloc[-1])
                except (ValueError, TypeError):
                    pass

        # Get energy from eplusmtr.csv (Joules -> kWh)
        df_mtr = self._read_meter_csv()
        if df_mtr is not None and len(df_mtr) > 0:
            # Target the total facility electricity column
            facility_cols = [c for c in df_mtr.columns if "Facility" in c and "[J]" in c]
            if not facility_cols:
                # fallback: sum all electricity columns
                facility_cols = [c for c in df_mtr.columns if "Electricity" in c and "[J]" in c]
            if facility_cols:
                total_j = float(df_mtr[facility_cols[0]].sum())
                metrics["total_energy_kwh"] = total_j / 3_600_000.0

        return metrics

    def get_total_energy(self):
        """Return total kWh consumed in this run"""
        m = self.read_latest()
        return m.get("total_energy_kwh", 0)
