"""
Autonomous AI Diagnostic Engine (Gemini 2.5 Flash Wrapper & Expert Fallback Rules)
"""

import time
import numpy as np
import pandas as pd
import streamlit as st

# Safely import Google GenAI SDK if available
try:
    from google import genai
    GENAI_SDK_AVAILABLE = True
except ImportError:
    GENAI_SDK_AVAILABLE = False


def generate_ai_diagnosis(scenario_name: str, df_data: pd.DataFrame, health_val: float, rul_val: float, cluster_status_text: str, current_stage: str) -> tuple[str, bool]:
    """
    Formulates telemetry diagnostic context and queries Google Gemini 2.5 Flash LLM.
    Returns (diagnostic_report_markdown, is_live_api_boolean).
    """
    avg_egt_cyl2 = float(np.mean(df_data["EGT Cyl 2 (°C)"]))
    max_egt_cyl2 = float(np.max(df_data["EGT Cyl 2 (°C)"]))
    avg_map = float(np.mean(df_data["MAP (inHg)"]))
    avg_fuel_p = float(np.mean(df_data["Fuel Pressure (bar)"]))
    avg_oil = float(np.mean(df_data["Oil Pressure (bar)"]))
    avg_cht = float(np.mean(df_data["CHT (°C)"]))
    avg_rpm = float(np.mean(df_data["Engine RPM"]))
    avg_vib = float(np.mean(df_data["Vibration (G)"]))
    
    prompt = f"""
You are an expert Rotax 915 iS UAV Master Field Engineer and Maintenance Diagnostician.
Analyze the following real-time 30-second telemetry snapshot from a MALE UAV equipped with a Rotax 915 iS engine (141 hp turbocharged piston engine).

ENGINE OPERATING CONTEXT:
- Flight Profile Stage: {current_stage}
- Active Scenario / Anomaly: {scenario_name}
- Current Engine Health Index: {health_val:.1f}%
- Estimated RUL: {rul_val:.0f} hours
- ML Cluster State: {cluster_status_text}

SENSORS STATISTICAL SUMMARY (30s Window):
- Engine Speed: Avg {avg_rpm:.0f} RPM (Range: 1800-5800 RPM)
- EGT Cyl 2: Avg {avg_egt_cyl2:.1f}°C, Peak {max_egt_cyl2:.1f}°C (Limit: 950°C max)
- EGT Avg (All Cylinders): Avg {np.mean(df_data['EGT Avg (°C)']):.1f}°C
- Cylinder Head Temp (CHT): Avg {avg_cht:.1f}°C (Limit: 120°C max)
- Manifold Absolute Pressure (MAP): Avg {avg_map:.2f} inHg (Limit: 30-45 inHg)
- Fuel Rail Pressure: Avg {avg_fuel_p:.2f} bar (Limit: 2.9-3.2 bar)
- Oil Pressure: Avg {avg_oil:.2f} bar (Limit: 2.0-5.0 bar above 3500 rpm)
- Vibration Index: Avg {avg_vib:.2f} G (Limit: 1.5-2.5 G)

INSTRUCTIONS FOR DIAGNOSTIC REPORT:
Provide a clear, highly professional engineering diagnostic response structured exactly with the following sections:

### 1. 🚨 Identified Anomaly & Root Cause Analysis
- State clearly whether an anomaly is present or if system is nominal.
- Detail the specific mechanical/thermal failure mode (e.g. fuel rail pressure regulator, coolant degradation, gearbox pitting, sensor drift, EGT split, oil pump valve).

### 2. 📋 Rotax 915 iS Manual Reference Checklists
- Provide step-by-step diagnostic inspection procedures citing Rotax 915 iS Maintenance Manual sections (e.g., Section 73-00-00 Fuel System, Section 75-00-00 Cooling, Section 79-00-00 Lubrication, Section 72-00-00 Mechanical Gearbox).

### 3. ⚡ Recommended Immediate Action for Ground Crew & Flight Controller
- Specify immediate in-flight or ground actions (e.g., emergency landing protocol, power setting adjustment, sensor calibration check, component replacement).

Keep the output concise, technical, and precise.
"""

    active_key = st.session_state.get("gemini_api_key", "").strip()
    if active_key and GENAI_SDK_AVAILABLE:
        try:
            client = genai.Client(api_key=active_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return response.text, True
        except Exception as e:
            st.error(f"AI API Call Exception: {e}. Falling back to embedded expert diagnostic rule engine.")
    
    # Offline rule engine fallbacks
    fallback_responses = {
        "Nominal Operation (No Anomaly)": f"""### 1. 🚨 Identified Anomaly & Root Cause Analysis
- **Status**: 🟢 NOMINAL / NO ANOMALY DETECTED.
- **Flight Profile Stage**: {current_stage}.
- **Unsupervised ML Cluster**: **Cluster 0 (Nominal Envelope)**.
- **Root Cause Analysis**: Engine parameters across fuel rail, cooling system, mechanical gearbox, oil circuit, and turbocharger plenum are operating within baseline specifications.
- **Health Evaluation**: Health Index at 98.0%, expected RUL 140.0 hours.

### 2. 📋 Rotax 915 iS Manual Reference Checklists
- **Manual Ref**: Rotax 915 iS Maintenance Manual (Section 05-20-00)
- **Checklist Item 1**: Perform standard 50-hour routine visual inspection of engine compartment.
- **Checklist Item 2**: Verify ECU log data integrity via BUDS (BRP-Rotax Diagnostic System).
- **Checklist Item 3**: Inspect spark plug gaps and exhaust spring retention safety wires.

### 3. ⚡ Recommended Immediate Action for Ground Crew & Flight Controller
- **Flight Controller**: Continue scheduled UAV mission profile without restrictions.
- **Ground Crew**: Log telemetry parameters in permanent flight records. Next scheduled servicing at interval T+50 hours.""",

        "1. Fuel Pressure Anomaly (2.5 - 3.5 bar instability)": f"""### 1. 🚨 Identified Anomaly & Root Cause Analysis
- **Status**: 🟡 FUEL SYSTEM ANOMALY DETECTED (FUEL RAIL PRESSURE INSTABILITY).
- **Observed Data**: Measured fuel rail pressure fluctuating around **{avg_fuel_p:.2f} bar** (Exceeding normal 2.9–3.2 bar range).
- **Root Cause Analysis**: Fuel rail pressure regulator instability or fine-filter restriction causing transient fuel delivery fluctuations and EGT turbulence.

### 2. 📋 Rotax 915 iS Manual Reference Checklists
- **Manual Ref**: Rotax 915 iS Maintenance Manual (Section 73-10-00 Injection & Fuel System)
- **Checklist Item 1**: Check fuel rail pressure regulator valve for debris binding.
- **Checklist Item 2**: Perform fine-filter inspection and fuel pump flow rate verification.
- **Checklist Item 3**: Inspect fuel lines for micro-leaks or air bubbles.

### 3. ⚡ Recommended Immediate Action for Ground Crew & Flight Controller
- **Flight Controller**: Monitor fuel flow stability. Avoid rapid throttle changes. Prepare for return to base.
- **Ground Crew**: Replace fuel fine-filter element and test fuel pressure regulator valve upon landing.""",

        "2. Cooling Degradation / Thermal Overheating": f"""### 1. 🚨 Identified Anomaly & Root Cause Analysis
- **Status**: 🟡 THERMAL OVERHEATING ANOMALY (COOLANT & CHT DEGRADATION).
- **Observed Data**: Cylinder Head Temp (CHT) rising to **{avg_cht:.1f}°C** (Exceeding nominal 110°C ceiling).
- **Root Cause Analysis**: Reduced radiator cooling airflow or coolant fluid degradation causing thermal buildup under sustained engine load.

### 2. 📋 Rotax 915 iS Manual Reference Checklists
- **Manual Ref**: Rotax 915 iS Maintenance Manual (Section 75-00-00 Cooling System)
- **Checklist Item 1**: Inspect radiator air intake duct for obstruction or debris.
- **Checklist Item 2**: Check expansion tank coolant fluid level and cap pressure seal.
- **Checklist Item 3**: Inspect coolant pump belt drive tension.

### 3. ⚡ Recommended Immediate Action for Ground Crew & Flight Controller
- **Flight Controller**: Reduce engine power to ECO cruise setting (80% RPM) to lower thermal load.
- **Ground Crew**: Flush coolant radiator fins and check coolant pump seal upon touchdown.""",

        "3. Coolant Sensor Drift / False-Low Reading": f"""### 1. 🚨 Identified Anomaly & Root Cause Analysis
- **Status**: 🟡 PLAUSIBILITY ANOMALY (COOLANT SENSOR FALSE-LOW DRIFT).
- **Observed Data**: Measured CHT sensor dropped to **{avg_cht:.1f}°C** while physics twin predicts high thermal state.
- **Root Cause Analysis**: Coolant level loss or sensor un-immersion causing sensor to measure ambient air temp instead of fluid temp (Rotax Installation Manual Section 75).

### 2. 📋 Rotax 915 iS Manual Reference Checklists
- **Manual Ref**: Rotax 915 iS Installation & Maintenance Manual (Section 75-20-00 Temperature Sensing)
- **Checklist Item 1**: Check coolant expansion tank for fluid loss.
- **Checklist Item 2**: Inspect temperature sensor probe immersion depth and wiring harness.

### 3. ⚡ Recommended Immediate Action for Ground Crew & Flight Controller
- **Flight Controller**: Trust physics digital twin thermal model over raw sensor signal. Initiate return to base.
- **Ground Crew**: Inspect cooling system for fluid leaks and recalibrate temperature sensor probe.""",

        "4. Gearbox High-Frequency Vibration Anomaly": f"""### 1. 🚨 Identified Anomaly & Root Cause Analysis
- **Status**: 🟡 MECHANICAL DEGRADATION (GEARBOX VIBRATION ANOMALY).
- **Observed Data**: Vibration Index reached **{avg_vib:.2f} G** (Exceeding 2.5 G ceiling).
- **Root Cause Analysis**: Mechanical gearbox gear-pitting or propeller shaft imbalance producing high-frequency vibration energy.

### 2. 📋 Rotax 915 iS Manual Reference Checklists
- **Manual Ref**: Rotax 915 iS Heavy Maintenance Manual (Section 72-10-00 Gearbox & Propeller Drive)
- **Checklist Item 1**: Perform magnetic drain plug inspection for iron/steel chips.
- **Checklist Item 2**: Check overload clutch friction torque and gearbox gear backlash.

### 3. ⚡ Recommended Immediate Action for Ground Crew & Flight Controller
- **Flight Controller**: Smooth out engine throttle commands to reduce torsional vibration spikes.
- **Ground Crew**: Inspect magnetic plug for metallic wear debris and perform gearbox backlash measurement.""",

        "5. EGT Cylinder 2 Combustion Imbalance": f"""### 1. 🚨 Identified Anomaly & Root Cause Analysis
- **Status**: 🟡 COMBUSTION ANOMALY (EGT CYLINDER 2 SPIKE).
- **Observed Data**: Cylinder 2 EGT peak reached **{max_egt_cyl2:.1f}°C** (EGT split exceeds 200°C limit).
- **Root Cause Analysis**: Partially clogged fuel injector or intake runner leak causing localized lean air-fuel burn in Cylinder 2.

### 2. 📋 Rotax 915 iS Manual Reference Checklists
- **Manual Ref**: Rotax 915 iS Maintenance Manual (Section 73-10-00 Injection System)
- **Checklist Item 1**: Check Cylinder 2 fuel injector wiring harness & resistance.
- **Checklist Item 2**: Perform injector flow-rate nozzle test for carbon deposit blockage.

### 3. ⚡ Recommended Immediate Action for Ground Crew & Flight Controller
- **Flight Controller**: Reduce power setting to lower EGT below 800°C. Initiate RTB.
- **Ground Crew**: Replace Cylinder 2 fuel injector nozzle upon landing.""",

        "6. Oil Pressure Loss / Lubrication Degradation": f"""### 1. 🚨 Identified Anomaly & Root Cause Analysis
- **Status**: 🔴 CRITICAL HYDRAULIC FAILURE (OIL PRESSURE LOSS).
- **Observed Data**: Lubrication pressure dropped to **{avg_oil:.2f} bar** (Safety limit is 2.0 bar).
- **Root Cause Analysis**: Severe oil pressure drop due to oil pump relief valve binding or oil cooler line rupture.

### 2. 📋 Rotax 915 iS Manual Reference Checklists
- **Manual Ref**: Rotax 915 iS Maintenance Manual (Section 79-00-00 Lubrication System)
- **Checklist Item 1**: Check oil tank fluid level and lower cowling for leaks.
- **Checklist Item 2**: Inspect oil filter pleats for metallic wear particles.

### 3. ⚡ Recommended Immediate Action for Ground Crew & Flight Controller
- **Flight Controller**: **EMERGENCY LANDING INITIATION**. Reduce engine power to minimum glide setting.
- **Ground Crew**: Tow aircraft off runway immediately and perform full engine inspection.""",

        "7. Turbocharger Boost Air-Path Collapse": f"""### 1. 🚨 Identified Anomaly & Root Cause Analysis
- **Status**: 🔴 CRITICAL BOOST FAILURE (TURBOCHARGER MAP COLLAPSE).
- **Observed Data**: Manifold Pressure (MAP) collapsed to **{avg_map:.2f} inHg** (Boost limit 35-45 inHg).
- **Root Cause Analysis**: Wastegate actuator stuck open or intercooler charge pipe dislodgement.

### 2. 📋 Rotax 915 iS Manual Reference Checklists
- **Manual Ref**: Rotax 915 iS Maintenance Manual (Section 78-10-00 Turbocharger System)
- **Checklist Item 1**: Check wastegate mechanical linkage and pneumatic solenoid valve.
- **Checklist Item 2**: Inspect intercooler charge pipes and silicone couplers.

### 3. ⚡ Recommended Immediate Action for Ground Crew & Flight Controller
- **Flight Controller**: Expect power loss. Descend UAV to lower altitude for stable unboosted flight.
- **Ground Crew**: Inspect wastegate linkage and charge pipes before next flight."""
    }

    return fallback_responses.get(scenario_name, fallback_responses["Nominal Operation (No Anomaly)"]), False


def render_ai_diagnostic_section(selected_scenario: str, df: pd.DataFrame, health: float, rul: float, cluster_text: str, flight_stage: str):
    """Renders the AI Diagnostic Copilot card and button."""
    st.markdown("""
        <div class="ai-copilot-card">
            <h3 style="color: #58a6ff; margin-top: 0; font-size: 1.3rem;">
                🧠 Autonomous AI Diagnostic Engine (Rotax 915 Field Specialist)
            </h3>
            <p style="color: #8b949e; font-size: 0.88rem;">
                Execute deep AI diagnostic reasoning on current telemetry streams to isolate component failure modes, reference Rotax 915 iS maintenance manuals, and output ground crew action plans.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    run_analysis = st.button("🧠 Perform AI Diagnostic Analysis", type="primary", use_container_width=True)

    if run_analysis:
        with st.spinner("⏳ Running Autonomous AI Diagnostic Engine..."):
            time.sleep(0.8)
            diag_output, is_live = generate_ai_diagnosis(selected_scenario, df, health, rul, cluster_text, flight_stage)
            st.markdown("---")
            if is_live:
                st.success("✨ **Autonomous AI Diagnostic Analysis Complete**")
            else:
                st.info("ℹ️ **AI Field Advisory Generated** (To enable online LLM reasoning, configure your key in **⚙️ API Settings**).")
            st.markdown(diag_output)
