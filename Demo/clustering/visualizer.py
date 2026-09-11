"""Transparent, stage-aware reference analysis for synthetic telemetry."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.charts import CHART_COLORS, PLOT_CONFIG, apply_chart_layout
from components.statistics_table import SENSOR_COLUMNS
from config.engine_specs import ENGINE_SPECS


def _analysis_inputs(df, baseline_df, anomaly_scores, outlier_mask):
    references = df.attrs.get("reference_bands", {})
    if not references and baseline_df is not None:
        references = baseline_df.attrs.get("reference_bands", {})
    if not references:
        references = {
            column: {
                **ENGINE_SPECS[key],
                "nominal": (ENGINE_SPECS[key]["min"] + ENGINE_SPECS[key]["max"]) / 2,
                "tolerance": (ENGINE_SPECS[key]["max"] - ENGINE_SPECS[key]["min"]) / 2,
            }
            for column, _, key, _ in SENSOR_COLUMNS
            if key in ENGINE_SPECS and column in df
        }
    channel_scores = {}
    for column, reference in references.items():
        if column not in df:
            continue
        tolerance = max(float(reference["tolerance"]), 1e-9)
        channel_scores[column] = np.abs(df[column].to_numpy() - reference["nominal"]) / tolerance
    if anomaly_scores is None:
        scores = np.max(np.column_stack(list(channel_scores.values())), axis=1) if channel_scores else np.zeros(len(df))
    else:
        scores = np.asarray(anomaly_scores, dtype=float)
    if outlier_mask is not None:
        mask = np.asarray(outlier_mask, dtype=bool)
    elif anomaly_scores is None and channel_scores:
        # Compare measurements to the actual edges: a decimal such as 3.2
        # can otherwise become 1.0000000000000024 after normalization.
        mask = np.logical_or.reduce([
            (df[column].to_numpy() < references[column]["min"])
            | (df[column].to_numpy() > references[column]["max"])
            for column in channel_scores
        ])
    else:
        mask = scores > 1.0
    if anomaly_scores is None:
        scores[~mask] = np.minimum(scores[~mask], 1.0)
    return references, channel_scores, scores, mask


def _sample_markers(fig, times, values, mask, unit="", include_reference=True):
    for flagged, label, color in (
        (False, "Within reference", CHART_COLORS["green"]),
        (True, "Flagged sample", CHART_COLORS["red"]),
    ):
        selected = mask if flagged else ~mask
        if not np.any(selected) or (not flagged and not include_reference):
            continue
        fig.add_trace(go.Scatter(
            x=times[selected],
            y=values[selected],
            mode="markers",
            name=label,
            marker=dict(size=6 if not flagged else 8, color=color, symbol="circle" if not flagged else "diamond"),
            hovertemplate=f"%{{y:.2f}}{(' ' + unit) if unit else ''}<extra>{label}</extra>",
        ))


def render_clustering_visualizer(
    df: pd.DataFrame,
    is_outlier: bool,
    selected_scenario: str,
    baseline_df: pd.DataFrame | None = None,
    anomaly_scores=None,
    outlier_mask=None,
):
    """Show sample-level rule scores and the most affected sensor's residual."""
    if df.empty:
        st.info("No samples are available to analyze.")
        return
    references, channel_scores, scores, mask = _analysis_inputs(df, baseline_df, anomaly_scores, outlier_mask)
    times = df["Time (s)"].to_numpy()
    flagged_count = int(mask.sum())
    peak_index = int(np.argmax(scores))
    stage_reference = bool(df.attrs.get("reference_bands")) or (
        baseline_df is not None and bool(baseline_df.attrs.get("reference_bands"))
    )
    st.caption(
        "Rule-based analysis of the synthetic window. Each sample’s score is its largest sensor "
        f"departure from the {'flight-stage' if stage_reference else 'demo'} reference, divided by that sensor’s tolerance. "
        "A score above 1 flags the sample."
    )
    summary_a, summary_b, summary_c = st.columns(3)
    summary_a.metric("Flagged samples", f"{flagged_count} / {len(df)}")
    summary_b.metric("Peak departure", f"{scores[peak_index]:.2f}×", help="1× is the boundary of the demo reference band.")
    summary_c.metric("First flag", f"{times[np.flatnonzero(mask)[0]]:g} s" if flagged_count else "None")

    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown("**Departure over time**")
        st.caption("The largest normalized departure across all monitored sensors")
        fig = go.Figure()
        fig.add_hrect(y0=0, y1=1, fillcolor="rgba(92,224,174,0.07)", line_width=0)
        fig.add_hline(y=1, line_color=CHART_COLORS["amber"], line_dash="dash", line_width=1)
        fig.add_trace(go.Scatter(
            x=times,
            y=scores,
            mode="lines",
            name="Departure score",
            line=dict(color=CHART_COLORS["cyan"], width=2),
            showlegend=False,
            hovertemplate="%{y:.2f}× reference tolerance<extra>Departure</extra>",
        ))
        _sample_markers(fig, times, scores, mask, "×")
        apply_chart_layout(fig, height=340)
        fig.update_yaxes(title_text="Departure (× tolerance)", range=[0, max(1.4, float(scores.max()) * 1.15)])
        st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG, key="analysis_score")

    with right:
        if not channel_scores:
            st.info("Sensor references are unavailable for this window.")
            return
        column = max(channel_scores, key=lambda name: float(np.max(channel_scores[name])))
        reference = references[column]
        target = reference["nominal"]
        tolerance = reference["tolerance"]
        unit = reference.get("unit", "")
        label = next((label for name, label, _, _ in SENSOR_COLUMNS if name == column), column)
        values = df[column].to_numpy() - target
        st.markdown(f"**Most affected sensor · {label}**")
        st.caption(f"Observed minus stage target ({target:g} {unit})" if stage_reference else f"Observed minus demo reference center ({target:g} {unit})")
        fig = go.Figure()
        fig.add_hrect(y0=-tolerance, y1=tolerance, fillcolor="rgba(92,224,174,0.07)", line_width=0)
        for boundary in (-tolerance, tolerance):
            fig.add_hline(y=boundary, line_color=CHART_COLORS["amber"], line_dash="dash", line_width=1)
        fig.add_hline(y=0, line_color=CHART_COLORS["muted"], line_width=1, opacity=0.4)
        if baseline_df is not None and column in baseline_df:
            fig.add_trace(go.Scatter(
                x=baseline_df["Time (s)"],
                y=baseline_df[column] - target,
                mode="lines",
                name="Nominal trace",
                line=dict(color=CHART_COLORS["muted"], width=1.7, dash="dot"),
                hovertemplate=f"%{{y:+.2f}} {unit}<extra>Nominal residual</extra>",
            ))
        fig.add_trace(go.Scatter(
            x=times,
            y=values,
            mode="lines",
            name="Sensor residual",
            line=dict(color=CHART_COLORS["cyan"], width=2),
            showlegend=False,
            hovertemplate=f"%{{y:+.2f}} {unit}<extra>{label} residual</extra>",
        ))
        _sample_markers(fig, times, values, mask, unit)
        apply_chart_layout(fig, height=340)
        fig.update_yaxes(title_text=f"Departure ({unit})")
        st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG, key="analysis_residual")

    st.caption(
        "Shading marks the demo reference band. Red markers identify samples flagged by any sensor; "
        "the residual chart shows the sensor with the largest peak normalized departure."
    )
