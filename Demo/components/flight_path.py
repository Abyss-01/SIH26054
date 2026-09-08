"""
Interactive 7-Stage MALE UAV Flight Profile Graphic Component
"""

import numpy as np
import streamlit as st
import plotly.graph_objects as go

def render_flight_path_component(manual_scenario: str) -> tuple[float, str, str]:
    """
    Renders 7-Stage MALE UAV Flight Profile interactive slider & Plotly graphic.
    Returns (flight_distance_km, flight_stage_name, active_selected_scenario).
    """
    st.markdown("### ✈️ MALE UAV Flight Profile & Rotax 915 iS Operating Sequence")
    
    st.markdown("""
        <div class="flight-path-card">
            <p style="color: #8b949e; font-size: 0.88rem; margin: 0;">
                Slide along the 7 conceptual flight profile stages: <b>1. Warm-Up ➔ 2. Take-Off ➔ 3. Climb ➔ 4. Cruise ➔ 5. Loiter / Endurance ➔ 6. Descent / Return ➔ 7. Landing / Cooldown</b>.
            </p>
        </div>
    """, unsafe_allow_html=True)

    flight_dist = st.slider(
        "✈️ UAV Progress along Flight Profile Corridor (0 km ➔ 300 km)",
        min_value=0, max_value=300, value=140, step=5
    )

    # Determine 7 Flight Stages
    if flight_dist <= 20:
        flight_stage = "1. Warm-Up (ground)"
    elif flight_dist <= 50:
        flight_stage = "2. Take-Off"
    elif flight_dist <= 110:
        flight_stage = "3. Climb"
    elif flight_dist <= 180:
        flight_stage = "4. Cruise"
    elif flight_dist <= 240:
        flight_stage = "5. Loiter / Endurance"
    elif flight_dist <= 280:
        flight_stage = "6. Descent / Return"
    else:
        flight_stage = "7. Landing / Cooldown"

    if manual_scenario != "Auto (Follow Flight Profile Stages)":
        selected_scenario = manual_scenario
    else:
        selected_scenario = "Nominal Operation (No Anomaly)"

    # Render MALE UAV Flight Profile Graph
    path_x = np.linspace(0, 300, 150)
    path_alt = np.zeros_like(path_x)
    for i, x in enumerate(path_x):
        if x <= 20:
            path_alt[i] = 100.0  # Warm-Up (ground)
        elif x <= 50:
            path_alt[i] = 100.0 + (x - 20) * 100.0  # Take-Off rotation
        elif x <= 110:
            path_alt[i] = 3100.0 + (x - 50) * 115.0  # Climb to mission altitude ~10,000 m
        elif x <= 180:
            path_alt[i] = 10000.0  # High-altitude cruise
        elif x <= 240:
            # Loiter racetrack oscillation
            path_alt[i] = 10000.0 + 300.0 * np.sin(2 * np.pi * (x - 180) / 20.0)
        elif x <= 280:
            path_alt[i] = 10000.0 - (x - 240) * 230.0  # Descent and return
        else:
            path_alt[i] = 800.0 - (x - 280) * 35.0  # Landing & rollout

    uav_x = float(flight_dist)
    idx_closest = np.argmin(np.abs(path_x - uav_x))
    uav_y = float(path_alt[idx_closest])

    fig_path = go.Figure()

    # 7 Stage Color Bands
    fig_path.add_trace(go.Scatter(x=path_x[0:10], y=path_alt[0:10], mode='lines', name='1. Warm-Up (Ground)', line=dict(color='#8b949e', width=3)))
    fig_path.add_trace(go.Scatter(x=path_x[9:26], y=path_alt[9:26], mode='lines', name='2. Take-Off', line=dict(color='#d29922', width=3.5)))
    fig_path.add_trace(go.Scatter(x=path_x[25:56], y=path_alt[25:56], mode='lines', name='3. Climb', line=dict(color='#58a6ff', width=3.5)))
    fig_path.add_trace(go.Scatter(x=path_x[55:91], y=path_alt[55:91], mode='lines', name='4. Cruise', line=dict(color='#3fb950', width=3.5)))
    fig_path.add_trace(go.Scatter(x=path_x[90:121], y=path_alt[90:121], mode='lines', name='5. Loiter (Racetrack)', line=dict(color='#a371f7', width=3.5, dash='dash')))
    fig_path.add_trace(go.Scatter(x=path_x[120:141], y=path_alt[120:141], mode='lines', name='6. Descent', line=dict(color='#38bdf8', width=3.5)))
    fig_path.add_trace(go.Scatter(x=path_x[140:150], y=path_alt[140:150], mode='lines', name='7. Landing / Cooldown', line=dict(color='#8b949e', width=3)))

    # Waypoint Stage Labels
    stages_x = [10, 35, 80, 145, 210, 260, 290]
    stages_y = [500, 1800, 6500, 10800, 10800, 5000, 500]
    stages_labels = ["1. Warm-Up", "2. Take-Off", "3. Climb", "4. Cruise", "5. Loiter (ECO)", "6. Descent", "7. Landing"]
    
    fig_path.add_trace(go.Scatter(
        x=stages_x, y=stages_y, mode='markers+text', name='Flight Stages',
        marker=dict(size=8, color='#58a6ff', symbol='square'),
        text=stages_labels, textposition="top center", textfont=dict(color='#c9d1d9', size=11)
    ))

    # Active UAV Marker
    uav_color = "#3fb950" if selected_scenario == "Nominal Operation (No Anomaly)" else "#f85149"
    fig_path.add_trace(go.Scatter(
        x=[uav_x], y=[uav_y], mode='markers+text', name='Active UAV Drone Position',
        marker=dict(size=18, color=uav_color, symbol='triangle-up', line=dict(width=2, color='#ffffff')),
        text=[f"🛸 UAV ({flight_stage})"], textposition="bottom center", textfont=dict(color='#ffffff', size=12, family='sans-serif')
    ))

    fig_path.update_layout(
        paper_bgcolor='#161b22', plot_bgcolor='#0d1117',
        font=dict(color='#c9d1d9', family='sans-serif'),
        margin=dict(l=50, r=50, t=50, b=60),
        xaxis=dict(title="Flight Distance / Mission Time (km)", gridcolor='#21262d', range=[-10, 310]),
        yaxis=dict(title="Altitude AGL (m)", gridcolor='#21262d', range=[-500, 12500]),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5),
        height=340
    )
    st.plotly_chart(fig_path, use_container_width=True)

    return flight_dist, flight_stage, selected_scenario
