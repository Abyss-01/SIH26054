"""A compact snapshot summary derived from the displayed telemetry."""
from html import escape
import streamlit as st


def render_top_metric_cards(telemetry):
    health = telemetry["health"]
    status = telemetry["status_label"]
    color = {"NORMAL": "#5ce0ae", "WARNING": "#f7bb60", "CRITICAL": "#ff6b7a"}.get(status, "#40d9e6")
    total = len(telemetry["df"])
    flagged = int(telemetry["outlier_mask"].sum())
    peak = float(max(telemetry["anomaly_scores"]))
    cards = [
        ("Demo health score", f'{health:.0f}<small> / 100</small>', "Based on this snapshot’s measured departures", f'<div class="metric-bar"><span style="width:{health}%;background:{color}"></span></div>'),
        ("Snapshot status", escape(status.title()), "Within reference" if not flagged else "Departure from stage reference", ""),
        ("Flagged samples", f'{flagged}<small> / {total}</small>', f"{flagged / total:.0%} of the 30-second window", ""),
        ("Peak anomaly score", f'{peak:.2f}<small> ×</small>', "Samples above 1.00 × are flagged", ""),
    ]
    for column, (label, value, note, extra) in zip(st.columns(4), cards):
        with column:
            st.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value" style="color:{color}">{value}</div><div class="metric-subtext">{note}</div>{extra}</div>', unsafe_allow_html=True)
