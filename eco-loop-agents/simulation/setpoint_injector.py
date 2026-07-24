from eppy.modeleditor import IDF
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BASELINE_IDF, TEMP_MIN_C, TEMP_MAX_C

# Eppy requires the IDD file path to be set before loading any IDF
IDF.setiddname(r"C:\EnergyPlusV23-2-0\Energy+.idd")

class SetpointInjector:
    def __init__(self):
        self.current_idf_path = BASELINE_IDF
        
    def load_idf(self, path=None):
        return IDF(path or self.current_idf_path)
    
    def set_zone_cooling_setpoint(self, zone_name: str, temp_c: float, output_path: str):
        """Set the cooling setpoint for a zone and save modified IDF"""
        # Clamp to safe range
        temp_c = max(TEMP_MIN_C, min(TEMP_MAX_C, temp_c))
        
        idf = self.load_idf()
        schedules = idf.idfobjects["SCHEDULE:COMPACT"]
        
        for sched in schedules:
            if zone_name.upper() in sched.Name.upper() and "COOL" in sched.Name.upper():
                # Find value fields and update
                for field in sched.fieldnames:
                    val = getattr(sched, field, None)
                    try:
                        # Assuming values > 20 are temperatures in Celsius
                        if float(val) >= 20:  
                            setattr(sched, field, temp_c)
                    except (TypeError, ValueError):
                        pass
        
        idf.save(output_path)
        return output_path
    
    def apply_ecm_natural_ventilation(self, idf_path: str, output_path: str):
        """Apply natural ventilation ECM"""
        idf = self.load_idf(idf_path)
        # Placeholder for modifying ventilation objects
        idf.save(output_path)
        return output_path
