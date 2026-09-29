"""Entry point for the UAV engine telemetry demonstration."""
import os
import streamlit as st
from Demo.config.scenarios import AUTO_SCENARIO, SCENARIO_LABELS, SCENARIO_OPTIONS
from Demo.styles.theme import apply_custom_theme
from Demo.views.dashboard import render_dashboard_view
from Demo.views.settings import render_settings_view
from Demo.ai_engine.copilot import GEMINI_MODEL


st.set_page_config(
    page_title="AERIS · Engine telemetry",
    page_icon="✧",
    layout="wide",
    initial_sidebar_state="auto",
)
apply_custom_theme()

DEFAULTS = {
    "active_page": "dashboard",
    "gemini_api_key": os.environ.get("GEMINI_API_KEY", ""),
    "manual_scenario": AUTO_SCENARIO,
    "noise_level": 1.0,
    "sample_seed": 42,
    "flight_distance": 140,
    "mission_playing": False,
    "show_baseline": True,
    "show_table_summary": False,
    "gemini_model": os.environ.get("GEMINI_MODEL", "").strip() or GEMINI_MODEL,
}

for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)
# Keep mission controls alive across the settings-page hide/show boundary.
# Direct re-assignment is what actually pins a widget-owned session key in
# Streamlit; setdefault alone is not enough when the owning widget is hidden.
for key in (
    "manual_scenario", "noise_level", "flight_distance", "show_baseline",
    "show_table_summary", "gemini_model",
):
    st.session_state[key] = st.session_state[key]

# Apply any overrides from a shareable URL query string.
for param, key, converter, valid in (
    ("scenario", "manual_scenario", str, lambda v: v in SCENARIO_OPTIONS),
    ("noise", "noise_level", float, None),
    ("seed", "sample_seed", int, None),
    ("distance", "flight_distance", int, None),
):
    if param in st.query_params:
        try:
            value = converter(st.query_params[param])
            if valid is None or valid(value):
                st.session_state[key] = value
        except (ValueError, TypeError):
            pass


def stop_playback():
    st.session_state["mission_playing"] = False


def reset_demo():
    for key in (
        "manual_scenario", "noise_level", "sample_seed",
        "flight_distance", "mission_playing", "show_baseline", "show_table_summary",
    ):
        st.session_state[key] = DEFAULTS[key]


def _update_query_params():
    """Write the current session state into the browser URL for sharing."""
    st.query_params["scenario"] = st.session_state["manual_scenario"]
    st.query_params["noise"] = str(st.session_state["noise_level"])
    st.query_params["seed"] = str(st.session_state["sample_seed"])
    st.query_params["distance"] = str(st.session_state["flight_distance"])


def _copy_share_link():
    _update_query_params()
    st.session_state["_share_link_copied"] = True


def _render_playback_indicator():
    playing = st.session_state.get("mission_playing", False)
    color = "#5ce0ae" if playing else "#91a4ba"
    bg = "rgba(92,224,174,0.10)" if playing else "rgba(145,164,186,0.06)"
    label = "▶  Playing" if playing else "■  Paused"
    st.markdown(
        f'<div style="display:inline-block;padding:0.2rem 0.7rem;border-radius:4px;'
        f'background:{bg};color:{color};font-weight:600;font-size:.78rem;'
        f'letter-spacing:.04em;border:1px solid {color}22;">{label}</div>',
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brand-symbol">✧</span><div>AERIS'
        '<span class="brand-sub">ENGINE INTELLIGENCE</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sidebar-label">WORKSPACE</div>', unsafe_allow_html=True)
    st.radio(
        "Workspace",
        ["dashboard", "settings"],
        key="active_page",
        format_func=lambda page: "Mission console" if page == "dashboard" else "AI configuration",
        label_visibility="collapsed",
        on_change=stop_playback,
    )
    st.divider()

    if st.session_state["active_page"] == "dashboard":
        st.markdown('<div class="sidebar-label">SCENARIO LAB</div>', unsafe_allow_html=True)
        st.selectbox(
            "Fault scenario",
            SCENARIO_OPTIONS,
            key="manual_scenario",
            format_func=lambda scenario: SCENARIO_LABELS[scenario],
            help="Guided-tour mode steps through a different fault at each flight stage. "
                 "Pick a fixed fault to hold it throughout the mission.",
            on_change=stop_playback,
        )
        st.caption("Change the scenario to compare an injected fault with the expected engine response.")
        st.slider("Sensor noise", 0.1, 2.0, step=0.1, key="noise_level", on_change=stop_playback)
        st.checkbox("Show nominal reference", key="show_baseline")
        st.checkbox(
            "Show table summary",
            key="show_table_summary",
            help="Show sensor statistics below the charts in the Telemetry tab. "
                 "The full table is also available in Table Summary.",
        )
        st.button("Reset demo", on_click=reset_demo, width="stretch")
        _render_playback_indicator()
        st.divider()
        with st.expander("About this simulation"):
            st.write(
                "A 300 km conceptual mission with seven flight stages and seven injectable faults. "
                "Each snapshot contains 30 synthetic samples at 1 Hz."
            )
            st.caption(
                "Reference bands and health scores are demonstration assumptions. "
                "This prototype does not estimate remaining engine life or connect to an aircraft."
            )
        st.divider()
        st.markdown('<div class="sidebar-label">SHARE</div>', unsafe_allow_html=True)
        st.button("Copy share link", width="stretch", on_click=_copy_share_link)
        if st.session_state.pop("_share_link_copied", False):
            st.success(
                "Link copied — paste it to open this scenario, noise, seed, and mission position."
            )

    active_key = st.session_state.get("gemini_api_key", "").strip()
    st.markdown(
        '<div class="sidebar-system"><span class="system-dot"></span> '
        + ("Gemini key configured" if active_key else "Offline diagnostics ready")
        + '<small>ROTAX 915 iS · SIH26054</small></div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="topline"><span>UAV SYSTEMS <span class="breadcrumb">/</span> '
    + ("MISSION CONSOLE" if st.session_state["active_page"] == "dashboard" else "AI CONFIGURATION")
    + '</span><span class="demo-badge"><span></span> SIMULATION · SYNTHETIC DATA</span></div>',
    unsafe_allow_html=True,
)

if st.session_state["active_page"] == "settings":
    render_settings_view()
else:
    render_dashboard_view(st.session_state["manual_scenario"], st.session_state["noise_level"])

st.markdown(
    '<div class="app-footer"><span>AERIS / Engine intelligence</span>'
    '<span>SIH 2026 · SIH26054 · Synthetic demonstration data</span></div>',
    unsafe_allow_html=True,
)
