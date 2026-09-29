"""Interactive mission profile and deterministic presentation controls."""
from html import escape
import time

import numpy as np
import plotly.graph_objects as go
import streamlit as st
from Demo.config.scenarios import FLIGHT_STAGES, NOMINAL_SCENARIO, SCENARIO_LABELS, resolve_scenario, stage_at_distance

STAGE_POSITIONS = (10, 35, 80, 145, 210, 260, 295)
STAGE_BOUNDS = (0, 20, 50, 110, 180, 240, 280, 300)
STAGE_NAMES = ("Warm-up", "Take-off", "Climb", "Cruise", "Loiter", "Descent", "Landing")


def altitude_at_distance(distance):
    """Conceptual altitude corridor; distance and altitude are not aircraft limits."""
    x = np.asarray(distance, dtype=float)
    altitude = np.interp(x, (0, 20, 50, 110, 240, 280, 300), (0, 0, 1800, 6500, 6500, 600, 0))
    return altitude + np.where((x > 180) & (x < 240), 100 * np.sin(2 * np.pi * (x - 180) / 20), 0)


def move_stage(direction):
    current = FLIGHT_STAGES.index(stage_at_distance(st.session_state["flight_distance"]))
    st.session_state["flight_distance"] = STAGE_POSITIONS[max(0, min(6, current + direction))]
    st.session_state["mission_playing"] = False


def pause_mission():
    st.session_state["mission_playing"] = False


def advance_mission(now=None):
    """Advance at most one 5 km step per timer tick, stopping at mission end."""
    now = time.monotonic() if now is None else now
    if st.session_state.get("mission_playing") and now - st.session_state.get("last_mission_tick", now) >= 1.8:
        st.session_state["flight_distance"] = min(300, st.session_state["flight_distance"] + 5)
        st.session_state["last_mission_tick"] = now
        if st.session_state["flight_distance"] == 300:
            st.session_state["mission_playing"] = False
            return True
    return False


def build_flight_figure(distance, selected_scenario):
    x = np.unique(np.concatenate((np.linspace(0, 300, 301), [distance])))
    y = altitude_at_distance(x)
    active_altitude = float(altitude_at_distance(distance))
    color = "#5ce0ae" if selected_scenario == NOMINAL_SCENARIO else "#f7bb60"
    fig = go.Figure()
    for i in range(7):
        fig.add_vrect(x0=STAGE_BOUNDS[i], x1=STAGE_BOUNDS[i+1], fillcolor="#40d9e6" if i == FLIGHT_STAGES.index(stage_at_distance(distance)) else "#20344a", opacity=.08 if i % 2 == 0 else .04, line_width=0)
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color="#38536b", width=2, dash="dot"), name="Planned corridor", fill="tozeroy", fillcolor="rgba(64,217,230,.025)", hovertemplate="%{x:.0f} km · %{y:,.0f} m<extra>Planned corridor</extra>"))
    flown = x <= distance
    fig.add_trace(go.Scatter(x=x[flown], y=y[flown], mode="lines", line=dict(color="#40d9e6", width=3), fill="tozeroy", fillcolor="rgba(64,217,230,.09)", name="Mission progress", hovertemplate="%{x:.0f} km · %{y:,.0f} m<extra>Mission progress</extra>"))
    fig.add_vline(x=distance, line_color="#40d9e6", line_width=1, line_dash="dot", opacity=.5)
    fig.add_trace(go.Scatter(x=[distance], y=[active_altitude], mode="markers", marker=dict(size=14, color=color, symbol="triangle-up", line=dict(color="#e8f0f8", width=2)), name="UAV position", hovertemplate=f"UAV · {distance} km<br>{active_altitude:,.0f} m<extra></extra>"))
    fig.update_layout(
        paper_bgcolor="#101d2e", plot_bgcolor="#0c1624", height=245,
        font=dict(color="#91a4ba", size=10, family="Inter, Segoe UI, sans-serif"),
        margin=dict(l=45, r=34, t=22, b=60), showlegend=False, hovermode="x unified",
        xaxis=dict(range=[-8, 318], tickvals=STAGE_POSITIONS, ticktext=STAGE_NAMES, tickangle=-35, automargin=True, gridcolor="#1c2c40", fixedrange=True, zeroline=False),
        yaxis=dict(title="Altitude · m", range=[-400, 8000], tickvals=[0, 3000, 6000], gridcolor="#1c2c40", fixedrange=True, zeroline=False),
    )
    return fig


def render_flight_path_component(manual_scenario: str) -> tuple[float, str, str]:
    st.markdown('<div class="section-heading"><h3>Mission profile</h3><span>7 STAGES / 300 KM CORRIDOR</span></div>', unsafe_allow_html=True)
    controls = st.columns([1.15, 1, 1, 3])
    with controls[0]:
        playing = st.session_state.get("mission_playing", False)
        if st.button("Pause mission" if playing else "Play mission", type="primary", width="stretch"):
            st.session_state["mission_playing"] = not playing
            if not playing:
                if st.session_state["flight_distance"] >= 300:
                    st.session_state["flight_distance"] = 0
                st.session_state["last_mission_tick"] = time.monotonic()
            st.rerun()
    with controls[1]:
        st.button("← Previous", on_click=move_stage, args=(-1,), disabled=st.session_state["flight_distance"] <= 20, width="stretch")
    with controls[2]:
        st.button("Next →", on_click=move_stage, args=(1,), disabled=st.session_state["flight_distance"] > 280, width="stretch")
    with controls[3]:
        st.slider(
            "Mission distance (km)",
            0, 300, step=5,
            key="flight_distance",
            label_visibility="visible",
            help="Drag to scrub through the mission — jump to any stage, not just play forward.",
            on_change=pause_mission,
        )
    distance = st.session_state["flight_distance"]
    flight_stage = stage_at_distance(distance)
    scenario = resolve_scenario(manual_scenario, flight_stage)
    st.plotly_chart(build_flight_figure(distance, scenario), width="stretch", config={"displayModeBar": False}, key="mission_profile")
    short_stage = STAGE_NAMES[FLIGHT_STAGES.index(flight_stage)]
    st.markdown(f'<div class="mission-strip"><span><strong>{escape(short_stage)}</strong> · {distance} / 300 km</span><span>{float(altitude_at_distance(distance)):,.0f} m simulated altitude</span><span>{escape(SCENARIO_LABELS[scenario])}</span></div>', unsafe_allow_html=True)
    return distance, flight_stage, scenario
