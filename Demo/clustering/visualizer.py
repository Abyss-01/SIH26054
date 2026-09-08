"""
Unsupervised ML Clustering Baseline Model & 2D Scatter Anomaly Visualizer
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

@st.cache_data(show_spinner=False)
def generate_trained_cluster_baseline(n_samples: int = 160) -> pd.DataFrame:
    """Generates baseline reference cluster points representing nominal Rotax 915 iS engine operations."""
    np.random.seed(101)
    return pd.DataFrame({
        "Engine RPM": np.random.normal(5400, 35.0, n_samples),
        "EGT (°C)": np.random.normal(802, 12.0, n_samples),
        "Oil Pressure (bar)": np.random.normal(4.0, 0.12, n_samples),
        "Vibration (G)": np.random.normal(2.0, 0.10, n_samples)
    })

def render_clustering_visualizer(df: pd.DataFrame, is_outlier: bool, selected_scenario: str):
    """Renders 2D Scatter Feature Space visualizers for Unsupervised ML Anomaly Detection."""
    st.markdown("### 🤖 Unsupervised ML Clustering & Anomaly Detection Visualizer")

    baseline_clusters = generate_trained_cluster_baseline()
    cc1, cc2 = st.columns(2)
    
    live_egt = df["EGT Cyl 2 (°C)"] if "Cylinder 2" in selected_scenario else df["EGT Avg (°C)"]
    live_color = "#f85149" if is_outlier else "#3fb950"
    live_symbol = "x" if is_outlier else "circle"
    live_label = "Current Telemetry (Outlier)" if is_outlier else "Current Telemetry (Cluster 0)"

    chart_theme = dict(
        paper_bgcolor='#161b22', plot_bgcolor='#0d1117',
        font=dict(color='#c9d1d9', family='sans-serif', size=11),
        margin=dict(l=50, r=50, t=50, b=60),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="center", x=0.5)
    )

    with cc1:
        fig_c1 = go.Figure()
        fig_c1.add_trace(go.Scatter(
            x=baseline_clusters["Engine RPM"], y=baseline_clusters["EGT (°C)"],
            mode='markers', name='Baseline Cluster 0 (Nominal Zone)',
            marker=dict(size=6, color='rgba(88, 166, 255, 0.45)')
        ))
        fig_c1.add_trace(go.Scatter(
            x=df["Engine RPM"], y=live_egt, mode='markers+lines', name=live_label,
            marker=dict(size=10, color=live_color, symbol=live_symbol, line=dict(width=1.5, color='#ffffff')),
            line=dict(color=live_color, width=1.5, dash='dot')
        ))
        
        layout_sc1 = chart_theme.copy()
        layout_sc1.update(
            title=dict(text="Feature Space 1: Engine Speed (RPM) vs. EGT (°C)", font=dict(size=13, color='#f0f6fc')),
            xaxis=dict(title="Engine Speed (RPM)", gridcolor='#21262d'),
            yaxis=dict(title="Exhaust Gas Temp (°C)", gridcolor='#21262d'),
            height=360
        )
        fig_c1.update_layout(**layout_sc1)
        st.plotly_chart(fig_c1, use_container_width=True)

    with cc2:
        fig_c2 = go.Figure()
        fig_c2.add_trace(go.Scatter(
            x=baseline_clusters["Oil Pressure (bar)"], y=baseline_clusters["Vibration (G)"],
            mode='markers', name='Baseline Cluster 0 (Nominal Zone)',
            marker=dict(size=6, color='rgba(163, 113, 247, 0.45)')
        ))
        fig_c2.add_trace(go.Scatter(
            x=df["Oil Pressure (bar)"], y=df["Vibration (G)"], mode='markers+lines', name=live_label,
            marker=dict(size=10, color=live_color, symbol=live_symbol, line=dict(width=1.5, color='#ffffff')),
            line=dict(color=live_color, width=1.5, dash='dot')
        ))
        
        layout_sc2 = chart_theme.copy()
        layout_sc2.update(
            title=dict(text="Feature Space 2: Oil Pressure (bar) vs. Vibration Index (G)", font=dict(size=13, color='#f0f6fc')),
            xaxis=dict(title="Oil Pressure (bar)", gridcolor='#21262d'),
            yaxis=dict(title="Vibration Index (G)", gridcolor='#21262d'),
            height=360
        )
        fig_c2.update_layout(**layout_sc2)
        st.plotly_chart(fig_c2, use_container_width=True)
