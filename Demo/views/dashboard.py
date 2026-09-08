"""
Digital Twin Dashboard View Page
"""

import streamlit as st
from telemetry.generator import generate_telemetry_data
from components.flight_path import render_flight_path_component
from components.metrics import render_top_metric_cards
from components.charts import render_telemetry_charts
from clustering.visualizer import render_clustering_visualizer
from components.statistics_table import render_statistics_table
from ai_engine.copilot import render_ai_diagnostic_section

def render_dashboard_view(manual_scenario: str, noise_level: float):
    """Renders the complete Digital Twin Dashboard view."""
    
    # 1. Flight Path Interactive Section
    flight_dist, flight_stage, selected_scenario = render_flight_path_component(manual_scenario)

    # 2. Telemetry Data Generation
    telemetry = generate_telemetry_data(selected_scenario, noise_level, flight_stage)
    df = telemetry["df"]
    health = telemetry["health"]
    rul = telemetry["rul"]
    status_label = telemetry["status_label"]
    status_class = telemetry["status_class"]
    status_desc = telemetry["status_desc"]
    cluster_text = telemetry["cluster_text"]
    cluster_sub = telemetry["cluster_sub"]
    cluster_color = telemetry["cluster_color"]
    is_outlier = telemetry["is_outlier"]

    # 3. Top Metric Cards
    render_top_metric_cards(
        health, rul, status_label, status_class, status_desc,
        cluster_text, cluster_sub, cluster_color
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Telemetry Stream Plotly Line Charts
    render_telemetry_charts(df, selected_scenario)

    # 5. Unsupervised ML Clustering Anomaly Visualizer
    render_clustering_visualizer(df, is_outlier, selected_scenario)

    # 6. Telemetry Statistics & Compliance Table
    render_statistics_table(df)

    st.markdown("<br>", unsafe_allow_html=True)

    # 7. Autonomous AI Diagnostic Copilot
    render_ai_diagnostic_section(selected_scenario, df, health, rul, cluster_text, flight_stage)
