"""
Telemetry Stream Plotly Line Charts Component
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def render_telemetry_charts(df: pd.DataFrame, selected_scenario: str):
    """Renders 4 separate Plotly line chart cards in a 2x2 grid with zero text/legend overlapping."""
    st.markdown("### 📊 Real-Time Rotax 915 iS Telemetry Stream (30s Window)")

    c1, c2 = st.columns(2)

    chart_theme = dict(
        paper_bgcolor='#161b22', plot_bgcolor='#0d1117',
        font=dict(color='#c9d1d9', family='sans-serif', size=11),
        margin=dict(l=50, r=50, t=50, b=60),
        xaxis=dict(title="Time (s)", gridcolor='#21262d'),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5)
    )

    with c1:
        # Chart 1: EGT by Cylinder
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=df["Time (s)"], y=df["EGT Cyl 1 (°C)"], name="EGT Cyl 1", line=dict(color="#58a6ff", width=2)))
        fig1.add_trace(go.Scatter(x=df["Time (s)"], y=df["EGT Cyl 2 (°C)"], name="EGT Cyl 2", line=dict(color="#f85149" if "Cylinder 2" in selected_scenario else "#a371f7", width=2.5)))
        fig1.add_trace(go.Scatter(x=df["Time (s)"], y=df["EGT Cyl 3 (°C)"], name="EGT Cyl 3", line=dict(color="#3fb950", width=2)))
        fig1.add_trace(go.Scatter(x=df["Time (s)"], y=df["EGT Cyl 4 (°C)"], name="EGT Cyl 4", line=dict(color="#d29922", width=2)))
        fig1.add_hline(y=950, line_dash="dash", line_color="#f85149", annotation_text="EGT Limit (950°C)")
        
        layout1 = chart_theme.copy()
        layout1.update(title=dict(text="Exhaust Gas Temp (EGT) by Cylinder (°C)", font=dict(size=14, color='#f0f6fc')), yaxis=dict(title="Temperature (°C)", gridcolor='#21262d'), height=340)
        fig1.update_layout(**layout1)
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        # Chart 2: MAP & RPM
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(go.Scatter(x=df["Time (s)"], y=df["MAP (inHg)"], name="MAP (inHg)", line=dict(color="#f472b6", width=2.5)), secondary_y=False)
        fig2.add_trace(go.Scatter(x=df["Time (s)"], y=df["Engine RPM"], name="Engine Speed (RPM)", line=dict(color="#a371f7", width=2, dash="dot")), secondary_y=True)
        fig2.add_hline(y=30, line_dash="dash", line_color="#8b949e", annotation_text="MAP Min (30 inHg)", secondary_y=False)
        
        layout2 = chart_theme.copy()
        layout2.update(title=dict(text="Manifold Absolute Pressure (MAP) & Engine RPM", font=dict(size=14, color='#f0f6fc')), height=340)
        fig2.update_layout(**layout2)
        fig2.update_yaxes(title_text="MAP (inHg)", gridcolor='#21262d', secondary_y=False)
        fig2.update_yaxes(title_text="Engine Speed (RPM)", gridcolor='#21262d', secondary_y=True)
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        # Chart 3: CHT & Fuel Rail Pressure
        fig3 = make_subplots(specs=[[{"secondary_y": True}]])
        fig3.add_trace(go.Scatter(x=df["Time (s)"], y=df["CHT (°C)"], name="CHT (°C)", line=dict(color="#d29922", width=2.5)), secondary_y=False)
        fig3.add_trace(go.Scatter(x=df["Time (s)"], y=df["Fuel Pressure (bar)"], name="Fuel Rail Press (bar)", line=dict(color="#38bdf8" if "Fuel Pressure" not in selected_scenario else "#f85149", width=2.5)), secondary_y=True)
        fig3.add_hline(y=120.0, line_dash="dash", line_color="#f85149", annotation_text="CHT Limit (120°C)", secondary_y=False)
        
        layout3 = chart_theme.copy()
        layout3.update(title=dict(text="Cylinder Head Temp (CHT) & Fuel Rail Pressure", font=dict(size=14, color='#f0f6fc')), height=340)
        fig3.update_layout(**layout3)
        fig3.update_yaxes(title_text="CHT (°C)", gridcolor='#21262d', secondary_y=False)
        fig3.update_yaxes(title_text="Fuel Rail Press (bar)", gridcolor='#21262d', secondary_y=True)
        st.plotly_chart(fig3, use_container_width=True)

    with c4:
        # Chart 4: Oil Pressure & Vibration Index
        fig4 = make_subplots(specs=[[{"secondary_y": True}]])
        fig4.add_trace(go.Scatter(x=df["Time (s)"], y=df["Oil Pressure (bar)"], name="Oil Press (bar)", line=dict(color="#3fb950" if "Oil Pressure" not in selected_scenario else "#f85149", width=2.5)), secondary_y=False)
        fig4.add_trace(go.Scatter(x=df["Time (s)"], y=df["Vibration (G)"], name="Vibration (G)", line=dict(color="#a855f7" if "Gearbox" not in selected_scenario else "#f85149", width=2.5)), secondary_y=True)
        fig4.add_hline(y=2.0, line_dash="dash", line_color="#f85149", annotation_text="Oil Min (2.0 bar)", secondary_y=False)
        fig4.add_hline(y=2.5, line_dash="dash", line_color="#d29922", annotation_text="Vib Ceiling (2.5 G)", secondary_y=True)
        
        layout4 = chart_theme.copy()
        layout4.update(title=dict(text="Lubrication Oil Pressure & Gearbox Vibration", font=dict(size=14, color='#f0f6fc')), height=340)
        fig4.update_layout(**layout4)
        fig4.update_yaxes(title_text="Oil Pressure (bar)", gridcolor='#21262d', secondary_y=False)
        fig4.update_yaxes(title_text="Vibration Index (G)", gridcolor='#21262d', secondary_y=True)
        st.plotly_chart(fig4, use_container_width=True)
