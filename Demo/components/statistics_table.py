"""Per-sensor statistics with explicit sample-level reference excursions."""

import pandas as pd
import streamlit as st

from Demo.config.engine_specs import ENGINE_SPECS


SENSOR_COLUMNS = [
    ("Engine RPM", "Engine speed", "RPM", "RPM"),
    *[(f"EGT Cyl {cylinder} (°C)", f"EGT cylinder {cylinder}", "EGT", "°C") for cylinder in range(1, 5)],
    ("EGT Avg (°C)", "EGT average", "EGT", "°C"),
    ("EGT Spread (°C)", "EGT cylinder spread", None, "°C"),
    ("CHT (°C)", "Cylinder head temperature", "CHT", "°C"),
    ("MAP (inHg)", "Manifold pressure", "MAP", "inHg"),
    ("Fuel Pressure (bar)", "Fuel pressure", "Fuel_Pressure", "bar"),
    ("Oil Pressure (bar)", "Oil pressure", "Oil_Pressure", "bar"),
    ("Vibration (G)", "Vibration", "Vibration", "G"),
]


def build_statistics_table(df: pd.DataFrame, baseline_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Summarize all samples; a single excursion remains visible in the table."""
    references = df.attrs.get("reference_bands", {})
    if not references and baseline_df is not None:
        references = baseline_df.attrs.get("reference_bands", {})
    rows = []
    for column, label, spec_key, unit in SENSOR_COLUMNS:
        if column not in df or df[column].empty:
            continue
        values = df[column]
        spec = ENGINE_SPECS.get(spec_key, {})
        reference = references.get(column, spec)
        lower, upper = reference.get("min"), reference.get("max")
        excursions = int(((values < lower) | (values > upper)).sum()) if lower is not None and upper is not None else None
        row = {
            "Sensor": label,
            "Unit": unit,
            "Latest": round(float(values.iloc[-1]), 2),
            "Minimum": round(float(values.min()), 2),
            "Maximum": round(float(values.max()), 2),
            "Mean": round(float(values.mean()), 2),
            "Demo reference": f"{lower:g}–{upper:g}" if lower is not None and upper is not None else "—",
            "Excursions": excursions,
            "Samples": len(values),
        }
        if baseline_df is not None and column in baseline_df and not baseline_df[column].empty:
            row["Latest Δ nominal"] = round(float(values.iloc[-1] - baseline_df[column].iloc[-1]), 2)
        rows.append(row)
    return pd.DataFrame(rows)


def render_statistics_table(df: pd.DataFrame, baseline_df: pd.DataFrame | None = None, key: str = "sensor_table_summary"):
    """Display a compact sensor table and return it for optional export."""
    summary = build_statistics_table(df, baseline_df)
    if summary.empty:
        st.info("No sensor samples are available for this window.")
        return summary
    has_stage_reference = bool(df.attrs.get("reference_bands")) or (
        baseline_df is not None and bool(baseline_df.attrs.get("reference_bands"))
    )
    st.markdown("**Table Summary · Sensor statistics**")
    caption = (
        "Each excursion is one sample outside that sensor’s stage-specific demo reference."
        if has_stage_reference
        else "Each excursion is one sample outside the illustrative demo bounds. "
        "These global bounds can include nominal warm-up and descent values."
    )
    if "Latest Δ nominal" in summary:
        caption += " Latest Δ nominal compares the last sample with the paired nominal trace."
    st.caption(caption)
    st.dataframe(
        summary,
        key=key,
        hide_index=True,
        width="stretch",
        height=min(500, 38 + 35 * len(summary)),
        column_config={
            "Latest": st.column_config.NumberColumn(format="%.2f"),
            "Minimum": st.column_config.NumberColumn(format="%.2f"),
            "Maximum": st.column_config.NumberColumn(format="%.2f"),
            "Mean": st.column_config.NumberColumn(format="%.2f"),
            "Latest Δ nominal": st.column_config.NumberColumn(format="%+.2f"),
            "Demo reference": st.column_config.TextColumn(help="Illustrative reference bands used by this demo."),
            "Excursions": st.column_config.NumberColumn(help="Number of individual samples outside the demo reference.", format="%d"),
        },
    )
    return summary
