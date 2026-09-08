"""
Sensor Statistics & Compliance Table Component
"""

import numpy as np
import pandas as pd
import streamlit as st
from config.engine_specs import ENGINE_SPECS

def render_statistics_table(df: pd.DataFrame):
    """Renders expandable telemetry statistics & threshold compliance table."""
    with st.expander("📋 Telemetry Statistics & Threshold Compliance Table", expanded=False):
        summary_data = []
        metrics_map = [
            ("Engine RPM", "Engine Speed", ENGINE_SPECS["RPM"]["min"], ENGINE_SPECS["RPM"]["max"], "RPM"),
            ("EGT Cyl 2 (°C)", "EGT Cyl 2", ENGINE_SPECS["EGT"]["min"], ENGINE_SPECS["EGT"]["max"], "°C"),
            ("EGT Avg (°C)", "EGT Average", ENGINE_SPECS["EGT"]["min"], ENGINE_SPECS["EGT"]["max"], "°C"),
            ("CHT (°C)", "Cylinder Head Temp", ENGINE_SPECS["CHT"]["min"], ENGINE_SPECS["CHT"]["max"], "°C"),
            ("MAP (inHg)", "Manifold Pressure", ENGINE_SPECS["MAP"]["min"], ENGINE_SPECS["MAP"]["max"], "inHg"),
            ("Fuel Pressure (bar)", "Fuel Rail Pressure", ENGINE_SPECS["Fuel_Pressure"]["min"], ENGINE_SPECS["Fuel_Pressure"]["max"], "bar"),
            ("Oil Pressure (bar)", "Oil Pressure", ENGINE_SPECS["Oil_Pressure"]["min"], ENGINE_SPECS["Oil_Pressure"]["max"], "bar"),
            ("Vibration (G)", "Vibration Index", ENGINE_SPECS["Vibration"]["min"], ENGINE_SPECS["Vibration"]["max"], "G")
        ]
        
        for col_name, label, min_val, max_val, unit in metrics_map:
            vals = df[col_name]
            mean_v = np.mean(vals)
            max_v = np.max(vals)
            min_v = np.min(vals)
            status_flag = "🟢 OK"
            if mean_v < min_val or mean_v > max_val or max_v > max_val * 1.02 or min_v < min_val * 0.95:
                status_flag = "🔴 OUT OF LIMITS" if (min_v < min_val * 0.85 or max_v > max_val * 1.04) else "🟡 WARNING"
                
            summary_data.append({
                "Sensor Metric": label,
                "Current Value": f"{vals.iloc[-1]:.1f} {unit}",
                "Average": f"{mean_v:.1f} {unit}",
                "Min - Max Range": f"{min_v:.1f} - {max_v:.1f} {unit}",
                "Nominal Limits": f"{min_val} - {max_val} {unit}",
                "Status": status_flag
            })
            
        st.table(pd.DataFrame(summary_data))
