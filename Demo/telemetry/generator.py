"""
Physics-Based Telemetry Data Generator
Generates realistic 1 Hz time-series data for Rotax 915 iS engine parameters
across 7 flight stages and 7 technical manual anomaly profiles.
"""

import numpy as np
import pandas as pd
import streamlit as st

@st.cache_data(show_spinner=False)
def generate_telemetry_data(scenario_key: str, noise_level: float = 1.0, flight_stage: str = "4. Cruise") -> dict:
    """
    Generates 30 seconds of realistic telemetry data for any flight stage / Rotax 915 anomaly.
    Returns dictionary containing telemetry DataFrame and health status metadata.
    """
    np.random.seed(42)
    time_steps = 30
    t = np.arange(time_steps)
    
    sine_fast = np.sin(2 * np.pi * t / 5.0) * 0.3
    sine_slow = np.cos(2 * np.pi * t / 15.0) * 0.5
    
    # Base defaults by flight stage
    if flight_stage == "1. Warm-Up (ground)":
        rpm_target = 2200.0
        egt_target = 760.0
        cht_target = 65.0
        map_target = 30.0
        fuel_p_target = 3.0
        oil_p_target = 4.8  # Cold oil higher pressure
        vib_target = 1.6
    elif flight_stage == "2. Take-Off":
        rpm_target = 5800.0  # Max power (104 kW)
        egt_target = 850.0
        cht_target = 115.0
        map_target = 44.5  # Full boost
        fuel_p_target = 3.1
        oil_p_target = 4.2
        vib_target = 2.2
    elif flight_stage == "3. Climb":
        rpm_target = 5600.0
        egt_target = 835.0
        cht_target = 112.0
        map_target = 42.0
        fuel_p_target = 3.05
        oil_p_target = 4.1
        vib_target = 2.1
    elif flight_stage == "4. Cruise":
        rpm_target = 5400.0  # Continuous power (99 kW)
        egt_target = 800.0
        cht_target = 108.0
        map_target = 40.0
        fuel_p_target = 3.0
        oil_p_target = 4.0
        vib_target = 2.0
    elif flight_stage == "5. Loiter / Endurance":
        rpm_target = 4900.0  # Fuel efficient ECO mode
        egt_target = 780.0
        cht_target = 102.0
        map_target = 36.0
        fuel_p_target = 3.0
        oil_p_target = 3.9
        vib_target = 1.8
    elif flight_stage == "6. Descent / Return":
        rpm_target = 3900.0
        egt_target = 760.0
        cht_target = 98.0
        map_target = 32.0
        fuel_p_target = 2.95
        oil_p_target = 3.8
        vib_target = 1.7
    else:  # 7. Landing / Cooldown
        rpm_target = 2000.0
        egt_target = 740.0
        cht_target = 90.0
        map_target = 29.0
        fuel_p_target = 2.95
        oil_p_target = 3.7
        vib_target = 1.5

    # Generate signal curves with noise
    rpm_base = rpm_target + sine_slow * 25.0 + np.random.normal(0, 15.0 * noise_level, time_steps)
    egt_cyl1_base = egt_target - 2.0 + sine_fast * 3.0 + np.random.normal(0, 2.0 * noise_level, time_steps)
    egt_cyl2_base = egt_target + 2.0 + sine_slow * 3.0 + np.random.normal(0, 2.5 * noise_level, time_steps)
    egt_cyl3_base = egt_target - 5.0 + sine_fast * 2.5 + np.random.normal(0, 2.0 * noise_level, time_steps)
    egt_cyl4_base = egt_target + 5.0 + sine_slow * 2.8 + np.random.normal(0, 2.2 * noise_level, time_steps)
    cht_base = cht_target + sine_slow * 1.5 + np.random.normal(0, 0.8 * noise_level, time_steps)
    map_base = map_target + sine_slow * 0.4 + np.random.normal(0, 0.25 * noise_level, time_steps)
    fuel_p_base = fuel_p_target + np.random.normal(0, 0.03 * noise_level, time_steps)
    oil_base = oil_p_target + sine_fast * 0.05 + np.random.normal(0, 0.04 * noise_level, time_steps)
    vib_base = vib_target + sine_fast * 0.1 + np.random.normal(0, 0.05 * noise_level, time_steps)

    # Nominal default state
    health = 98.0
    rul_hours = 140.0
    status_label = "NORMAL"
    status_class = "status-normal"
    status_desc = f"Nominal Operating Profile — {flight_stage}"
    cluster_text = "Cluster 0 (Nominal Envelope)"
    cluster_sub = "🟢 Inside Normal Physics Range"
    cluster_color = "#3fb950"
    is_outlier = False

    # Apply Selected Rotax 915 iS Anomaly Profile (from rotax_915is_anomalies.txt)
    if scenario_key == "1. Fuel Pressure Anomaly (2.5 - 3.5 bar instability)":
        health = 68.0
        rul_hours = 32.0
        status_label = "WARNING"
        status_class = "status-warning"
        status_desc = "Fuel Rail Pressure Out of Bounds (2.9 - 3.2 bar limit)"
        cluster_text = "OUTLIER / ANOMALY DETECTED"
        cluster_sub = "🔴 Fuel Rail Transients > 3.2 bar"
        cluster_color = "#f85149"
        is_outlier = True
        fuel_p_base = np.linspace(2.9, 2.4, time_steps) + np.random.normal(0, 0.25 * noise_level, time_steps)
        egt_cyl1_base += np.random.normal(0, 18.0, time_steps)
        egt_cyl2_base += np.random.normal(0, 18.0, time_steps)

    elif scenario_key == "2. Cooling Degradation / Thermal Overheating":
        health = 52.0
        rul_hours = 18.0
        status_label = "WARNING"
        status_class = "status-warning"
        status_desc = "Coolant Thermal Efficiency Degradation — CHT Rising Fast"
        cluster_text = "OUTLIER / ANOMALY DETECTED"
        cluster_sub = "🔴 Thermal Trend Residual Violation"
        cluster_color = "#f85149"
        is_outlier = True
        cht_base = np.linspace(cht_target, 126.0, time_steps) + np.random.normal(0, 1.2 * noise_level, time_steps)
        oil_base -= np.linspace(0, 0.6, time_steps)

    elif scenario_key == "3. Coolant Sensor Drift / False-Low Reading":
        health = 74.0
        rul_hours = 42.0
        status_label = "WARNING"
        status_class = "status-warning"
        status_desc = "Plausibility Anomaly: Measured CHT Drops Implausibly to 45°C Air Temp"
        cluster_text = "OUTLIER / ANOMALY DETECTED"
        cluster_sub = "🔴 Physics Twin vs Sensor Residual Mismatch"
        cluster_color = "#d29922"
        is_outlier = True
        cht_base = np.linspace(cht_target, 45.0, time_steps) + np.random.normal(0, 0.5 * noise_level, time_steps)

    elif scenario_key == "4. Gearbox High-Frequency Vibration Anomaly":
        health = 62.0
        rul_hours = 24.0
        status_label = "WARNING"
        status_class = "status-warning"
        status_desc = "Mechanical Degradation: Gearbox Pitting High-Frequency Vibration"
        cluster_text = "OUTLIER / ANOMALY DETECTED"
        cluster_sub = "🔴 Vibration RMS Exceeds 2.5 G Ceiling"
        cluster_color = "#f85149"
        is_outlier = True
        vib_base = np.linspace(2.0, 3.4, time_steps) + np.random.normal(0, 0.25 * noise_level, time_steps)

    elif scenario_key == "5. EGT Cylinder 2 Combustion Imbalance":
        health = 70.0
        rul_hours = 35.0
        status_label = "WARNING"
        status_class = "status-warning"
        status_desc = "Cylinder Combustion Anomaly: EGT Cyl 2 Peak Spikes Above 870°C"
        cluster_text = "OUTLIER / ANOMALY DETECTED"
        cluster_sub = "🔴 EGT Split > 200°C Limit"
        cluster_color = "#f85149"
        is_outlier = True
        egt_cyl2_base = np.linspace(egt_target, 885.0, time_steps) + np.random.normal(0, 3.0 * noise_level, time_steps)

    elif scenario_key == "6. Oil Pressure Loss / Lubrication Degradation":
        health = 28.0
        rul_hours = 4.0
        status_label = "CRITICAL"
        status_class = "status-critical"
        status_desc = "Hydraulic Failure: Lubrication Oil Pressure Drops Below 2.0 bar"
        cluster_text = "OUTLIER / ANOMALY DETECTED"
        cluster_sub = "🔴 Hydraulic Seizure Risk"
        cluster_color = "#f85149"
        is_outlier = True
        oil_base = np.linspace(3.8, 1.1, time_steps) + np.random.normal(0, 0.05 * noise_level, time_steps)
        cht_base += np.linspace(0, 14.0, time_steps)
        vib_base += np.linspace(0, 0.8, time_steps)

    elif scenario_key == "7. Turbocharger Boost Air-Path Collapse":
        health = 42.0
        rul_hours = 11.0
        status_label = "CRITICAL"
        status_class = "status-critical"
        status_desc = "Pneumatic Anomaly: Turbocharger MAP Collapses Below 35 inHg"
        cluster_text = "OUTLIER / ANOMALY DETECTED"
        cluster_sub = "🔴 Boost Plenum Loss"
        cluster_color = "#f85149"
        is_outlier = True
        map_base = np.linspace(map_target, 24.0, time_steps) + np.random.normal(0, 0.3 * noise_level, time_steps)
        rpm_base -= np.linspace(0, 600, time_steps)

    df = pd.DataFrame({
        "Time (s)": t,
        "Engine RPM": np.round(rpm_base, 1),
        "EGT Cyl 1 (°C)": np.round(egt_cyl1_base, 1),
        "EGT Cyl 2 (°C)": np.round(egt_cyl2_base, 1),
        "EGT Cyl 3 (°C)": np.round(egt_cyl3_base, 1),
        "EGT Cyl 4 (°C)": np.round(egt_cyl4_base, 1),
        "EGT Avg (°C)": np.round((egt_cyl1_base + egt_cyl2_base + egt_cyl3_base + egt_cyl4_base) / 4.0, 1),
        "CHT (°C)": np.round(cht_base, 1),
        "MAP (inHg)": np.round(map_base, 2),
        "Fuel Pressure (bar)": np.round(fuel_p_base, 2),
        "Oil Pressure (bar)": np.round(oil_base, 2),
        "Vibration (G)": np.round(vib_base, 2)
    })
    
    return {
        "df": df, "health": health, "rul": rul_hours,
        "status_label": status_label, "status_class": status_class, "status_desc": status_desc,
        "cluster_text": cluster_text, "cluster_sub": cluster_sub, "cluster_color": cluster_color, "is_outlier": is_outlier
    }
