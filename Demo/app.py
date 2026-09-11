"""Entry point for the UAV engine telemetry demonstration."""
import os
import streamlit as st
from config.scenarios import AUTO_SCENARIO, SCENARIO_LABELS, SCENARIO_OPTIONS
from styles.theme import apply_custom_theme
from views.dashboard import render_dashboard_view
from views.settings import render_settings_view
from ai_engine.copilot import GEMINI_MODEL

st.set_page_config(page_title="AERIS · Engine telemetry", page_icon="✧", layout="wide", initial_sidebar_state="auto")
apply_custom_theme()
DEFAULTS = {
    "active_page": "dashboard", "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
    "manual_scenario": AUTO_SCENARIO, "noise_level": 1.0, "sample_seed": 42,
    "flight_distance": 140, "mission_playing": False, "show_baseline": True,
    "show_table_summary": False,
    "gemini_model": os.environ.get("GEMINI_MODEL", "").strip() or GEMINI_MODEL,
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)
# Keep mission controls when their widgets are hidden on the settings page.
for key in ("manual_scenario", "noise_level", "flight_distance", "show_baseline", "show_table_summary", "gemini_model"):
    st.session_state[key] = st.session_state[key]


def stop_playback():
    st.session_state["mission_playing"] = False


def reset_demo():
    for key in ("manual_scenario", "noise_level", "sample_seed", "flight_distance", "mission_playing", "show_baseline", "show_table_summary"):
        st.session_state[key] = DEFAULTS[key]


with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-symbol">✧</span><div>AERIS<span class="brand-sub">ENGINE INTELLIGENCE</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-label">WORKSPACE</div>', unsafe_allow_html=True)
    st.radio("Workspace", ["dashboard", "settings"], key="active_page", format_func=lambda page: "Mission console" if page == "dashboard" else "AI configuration", label_visibility="collapsed", on_change=stop_playback)
    st.divider()
    if st.session_state["active_page"] == "dashboard":
        st.markdown('<div class="sidebar-label">SCENARIO LAB</div>', unsafe_allow_html=True)
        st.selectbox("Fault scenario", SCENARIO_OPTIONS, key="manual_scenario", format_func=lambda scenario: SCENARIO_LABELS[scenario], help="The guided tour changes faults with each mission stage. Select a fault to explore it at any stage.", on_change=stop_playback)
        st.caption("Change the scenario to compare an injected fault with the expected engine response.")
        st.slider("Sensor noise", 0.1, 2.0, step=0.1, key="noise_level", on_change=stop_playback)
        st.checkbox("Show nominal reference", key="show_baseline")
        st.checkbox("Show table summary", key="show_table_summary", help="Show sensor statistics below the charts in the Telemetry tab. The full table is also available in Table Summary.")
        st.button("Reset demo", on_click=reset_demo, width="stretch")
        st.divider()
        with st.expander("About this simulation"):
            st.write("A 300 km conceptual mission with seven flight stages and seven injectable faults. Each snapshot contains 30 synthetic samples at 1 Hz.")
            st.caption("Reference bands and health scores are demonstration assumptions. This prototype does not estimate remaining engine life or connect to an aircraft.")
    active_key = st.session_state.get("gemini_api_key", "").strip()
    st.markdown('<div class="sidebar-system"><span class="system-dot"></span> ' + ("Gemini key configured" if active_key else "Offline diagnostics ready") + '<small>ROTAX 915 iS · SIH26054</small></div>', unsafe_allow_html=True)

st.markdown('<div class="topline"><span>UAV SYSTEMS <span class="breadcrumb">/</span> ' + ("MISSION CONSOLE" if st.session_state["active_page"] == "dashboard" else "AI CONFIGURATION") + '</span><span class="demo-badge"><span></span> SIMULATION</span></div>', unsafe_allow_html=True)
if st.session_state["active_page"] == "settings":
    render_settings_view()
else:
    render_dashboard_view(st.session_state["manual_scenario"], st.session_state["noise_level"])
st.markdown('<div class="app-footer"><span>AERIS / Engine intelligence</span><span>SIH 2026 · SIH26054 · Synthetic demonstration data</span></div>', unsafe_allow_html=True)
