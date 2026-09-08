"""
Rotax 915 iS UAV Digital Twin & Predictive Maintenance Dashboard
Problem Statement: SIH 2026 SIH26054
Main Application Entry Point & Navigation Router
"""

import os
import streamlit as st

from styles.theme import apply_custom_theme
from views.dashboard import render_dashboard_view
from views.settings import render_settings_view

# 1. Page Configuration (Must be first Streamlit call)
st.set_page_config(
    page_title="Rotax 915 iS UAV Digital Twin & Telemetry Console",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Apply Custom Grafana/Palantir Dark Theme & CSS
apply_custom_theme()

# 2. Initialize Session State Variables
if "active_page" not in st.session_state:
    st.session_state["active_page"] = "dashboard"

if "gemini_api_key" not in st.session_state:
    st.session_state["gemini_api_key"] = os.environ.get("GEMINI_API_KEY", "")

# 3. Top Navigation Bar with Quick API Settings Gear Button
col_h1, col_h2 = st.columns([5, 1])

with col_h1:
    st.markdown("""
        <div class="app-header">
            <div>
                <h1 class="app-header-title">🛸 Rotax 915 iS UAV Digital Twin & Telemetry Console</h1>
                <p class="app-header-sub">SIH 2026 Problem Statement SIH26054 — MALE UAV Piston Engine Diagnostic Platform</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_h2:
    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
    if st.button("⚙️ API Settings", use_container_width=True):
        st.session_state["active_page"] = "settings"
        st.rerun()

# 4. Sidebar Controls & Navigation
with st.sidebar:
    st.markdown("### 🧭 Navigation & Views")
    
    nav_selection = st.radio(
        "Select View",
        ["🛸 Digital Twin Dashboard", "⚙️ API Settings"],
        index=0 if st.session_state["active_page"] == "dashboard" else 1
    )
    
    if nav_selection == "🛸 Digital Twin Dashboard" and st.session_state["active_page"] != "dashboard":
        st.session_state["active_page"] = "dashboard"
        st.rerun()
    elif nav_selection == "⚙️ API Settings" and st.session_state["active_page"] != "settings":
        st.session_state["active_page"] = "settings"
        st.rerun()

    st.divider()

    if st.session_state["active_page"] == "dashboard":
        st.markdown("### 🎛️ Anomaly Scenario Selector")
        manual_scenario = st.selectbox(
            "Fault Injection Mode",
            [
                "Auto (Follow Flight Profile Stages)",
                "Nominal Operation (No Anomaly)",
                "1. Fuel Pressure Anomaly (2.5 - 3.5 bar instability)",
                "2. Cooling Degradation / Thermal Overheating",
                "3. Coolant Sensor Drift / False-Low Reading",
                "4. Gearbox High-Frequency Vibration Anomaly",
                "5. EGT Cylinder 2 Combustion Imbalance",
                "6. Oil Pressure Loss / Lubrication Degradation",
                "7. Turbocharger Boost Air-Path Collapse"
            ],
            index=0,
            help="Select an anomaly candidate from Rotax 915 iS technical manuals."
        )
        
        st.divider()
        st.markdown("### ⚙️ Simulation Controls")
        noise_level = st.slider("Signal Noise Factor", 0.1, 2.0, 1.0, 0.1)
        
        st.divider()
        current_key = st.session_state.get("gemini_api_key", "").strip()
        if current_key:
            st.caption("🟢 **AI Diagnostic Core**: Online (`gemini-2.5-flash`)")
        else:
            st.caption("🟡 **AI Diagnostic Core**: Offline (Rule Engine)")
            
        st.divider()
        with st.expander("📖 Rotax 915 iS Envelope Limits"):
            st.markdown("""
            - **RPM**: 1,800 – 5,800 RPM
            - **EGT Limit**: Max 950°C (Nominal 800°C)
            - **CHT Limit**: Max 120°C (Nominal 110°C)
            - **MAP Boost**: 30 – 45 inHg (Nominal 40 inHg)
            - **Fuel Pressure**: 2.9 – 3.2 bar (Nominal 3.0 bar)
            - **Oil Pressure**: 2.0 – 5.0 bar (Nominal 4.0 bar)
            - **Vibration**: 1.5 – 2.5 G (Nominal 2.0 G)
            """)
    else:
        manual_scenario = "Auto (Follow Flight Profile Stages)"
        noise_level = 1.0

# 5. Route Execution to Views
if st.session_state["active_page"] == "settings":
    render_settings_view()
else:
    render_dashboard_view(manual_scenario, noise_level)

# 6. Global Footer
st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption("🛸 Rotax 915 iS UAV Digital Twin Platform | SIH 2026 Problem Statement SIH26054 | Built with Streamlit, NumPy, Plotly & Autonomous AI")
