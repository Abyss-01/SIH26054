"""Compact telemetry charts for the synthetic engine demonstration."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

CHART_COLORS = {
    "panel": "#101d2e",
    "plot": "#0c1624",
    "grid": "#23364b",
    "text": "#e8f0f8",
    "muted": "#91a4ba",
    "cyan": "#40d9e6",
    "green": "#5ce0ae",
    "amber": "#f7bb60",
    "red": "#ff6b7a",
    "purple": "#a999ff",
}

PLOT_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
    "scrollZoom": False,
}


def apply_chart_layout(fig: go.Figure, height: int = 330) -> go.Figure:
    """Keep chart text and legends readable within narrow dashboard columns."""
    fig.update_layout(
        paper_bgcolor=CHART_COLORS["panel"],
        plot_bgcolor=CHART_COLORS["plot"],
        font=dict(color=CHART_COLORS["text"], family="sans-serif", size=11),
        margin=dict(l=48, r=46, t=16, b=105),
        height=height,
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=CHART_COLORS["panel"],
            bordercolor=CHART_COLORS["grid"],
            font_color=CHART_COLORS["text"],
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.22,
            xanchor="left",
            x=0,
            font=dict(size=10),
            tracegroupgap=0,
        ),
    )
    fig.update_xaxes(
        title_text="Elapsed time (s)",
        title_font_size=11,
        gridcolor=CHART_COLORS["grid"],
        zeroline=False,
        automargin=True,
        tickfont_color=CHART_COLORS["muted"],
    )
    fig.update_yaxes(
        title_font_size=11,
        gridcolor=CHART_COLORS["grid"],
        zeroline=False,
        automargin=True,
        tickfont_color=CHART_COLORS["muted"],
    )
    return fig


def _trace(df, column, name, color, unit, nominal=False):
    return go.Scatter(
        x=df["Time (s)"],
        y=df[column],
        name=name,
        mode="lines",
        line=dict(color=color, width=1.4 if nominal else 2.3, dash="dot" if nominal else "solid"),
        opacity=0.55 if nominal else 1,
        hovertemplate=f"%{{y:,.2f}} {unit}<extra>{name}</extra>",
    )


def _reference(fig, value, secondary_y=None):
    kwargs = {"secondary_y": secondary_y} if secondary_y is not None else {}
    fig.add_hline(
        y=value,
        line_dash="dash",
        line_width=1,
        line_color=CHART_COLORS["amber"],
        opacity=0.55,
        **kwargs,
    )


def _band(df, column, fallback):
    reference = df.attrs.get("reference_bands", {}).get(column)
    return (reference["min"], reference["max"]) if reference else fallback


def _band_label(bounds):
    return f"{bounds[0]:g}–{bounds[1]:g}"


def _paired_chart(df, baseline_df, specs, references):
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for secondary, (column, name, color, unit, axis_title) in enumerate(specs):
        if baseline_df is not None and column in baseline_df:
            fig.add_trace(
                _trace(baseline_df, column, f"Nominal {name}", color, unit, nominal=True),
                secondary_y=bool(secondary),
            )
        fig.add_trace(_trace(df, column, name, color, unit), secondary_y=bool(secondary))
        fig.update_yaxes(title_text=axis_title, secondary_y=bool(secondary))
    for value, secondary in references:
        _reference(fig, value, secondary_y=secondary)
    apply_chart_layout(fig)
    fig.update_yaxes(showgrid=False, secondary_y=True)
    return fig


def render_telemetry_charts(
    df: pd.DataFrame,
    selected_scenario: str,
    baseline_df: pd.DataFrame | None = None,
    show_baseline: bool = True,
):
    """Plot the selected synthetic window with optional paired nominal traces."""
    if df.empty:
        st.info("No telemetry samples are available for this window.")
        return
    baseline = baseline_df if show_baseline else None
    reference_label = "stage demo" if df.attrs.get("reference_bands") else "demo"
    st.caption(
        "Solid lines show simulated sensor values; dotted lines show the stage nominal reference. "
        "Amber dashed lines mark illustrative reference bounds. Hover to inspect a sample."
        if baseline is not None
        else "Solid lines show simulated sensor values. Amber dashed lines mark illustrative reference bounds. "
        "Hover to inspect a sample."
    )
    first, second = st.columns(2, gap="medium")
    with first:
        st.markdown("**Exhaust temperatures**")
        cylinder_bands = [_band(df, f"EGT Cyl {i} (°C)", (750, 950)) for i in range(1, 5)]
        egt_band = (min(band[0] for band in cylinder_bands), max(band[1] for band in cylinder_bands))
        st.caption(f"Four cylinders · {reference_label} envelope {_band_label(egt_band)} °C")
        fig = go.Figure()
        if baseline is not None and "EGT Avg (°C)" in baseline:
            fig.add_trace(
                _trace(baseline, "EGT Avg (°C)", "Nominal avg", CHART_COLORS["muted"], "°C", nominal=True)
            )
        for cylinder, color in enumerate(("cyan", "purple", "green", "amber"), start=1):
            fig.add_trace(
                _trace(df, f"EGT Cyl {cylinder} (°C)", f"Cyl {cylinder}", CHART_COLORS[color], "°C")
            )
        for boundary in egt_band:
            _reference(fig, boundary)
        apply_chart_layout(fig)
        fig.update_yaxes(title_text="Temperature (°C)")
        st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG, key="telemetry_egt")
    with second:
        st.markdown("**Power & boost**")
        map_band = _band(df, "MAP (inHg)", (30, 45))
        rpm_band = _band(df, "Engine RPM", (1800, 5800))
        st.caption(f"{reference_label.capitalize()} · MAP {_band_label(map_band)} inHg · {_band_label(rpm_band)} RPM")
        fig = _paired_chart(
            df, baseline,
            [
                ("MAP (inHg)", "MAP", CHART_COLORS["cyan"], "inHg", "MAP (inHg)"),
                ("Engine RPM", "RPM", CHART_COLORS["purple"], "RPM", "Engine speed (RPM)"),
            ],
            [(value, False) for value in map_band] + [(value, True) for value in rpm_band],
        )
        st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG, key="telemetry_power")

    third, fourth = st.columns(2, gap="medium")
    with third:
        st.markdown("**Cooling & fuel delivery**")
        cht_band = _band(df, "CHT (°C)", (100, 120))
        fuel_band = _band(df, "Fuel Pressure (bar)", (2.9, 3.2))
        st.caption(f"{reference_label.capitalize()} · CHT {_band_label(cht_band)} °C · fuel {_band_label(fuel_band)} bar")
        fig = _paired_chart(
            df, baseline,
            [
                ("CHT (°C)", "CHT", CHART_COLORS["amber"], "°C", "CHT (°C)"),
                ("Fuel Pressure (bar)", "Fuel", CHART_COLORS["cyan"], "bar", "Fuel pressure (bar)"),
            ],
            [(value, False) for value in cht_band] + [(value, True) for value in fuel_band],
        )
        st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG, key="telemetry_cooling")
    with fourth:
        st.markdown("**Lubrication & vibration**")
        oil_band = _band(df, "Oil Pressure (bar)", (2.0, 5.0))
        vibration_band = _band(df, "Vibration (G)", (1.5, 2.5))
        st.caption(f"{reference_label.capitalize()} · oil {_band_label(oil_band)} bar · vibration {_band_label(vibration_band)} G")
        fig = _paired_chart(
            df, baseline,
            [
                ("Oil Pressure (bar)", "Oil", CHART_COLORS["green"], "bar", "Oil pressure (bar)"),
                ("Vibration (G)", "Vibration", CHART_COLORS["purple"], "G", "Vibration (G)"),
            ],
            [(value, False) for value in oil_band] + [(value, True) for value in vibration_band],
        )
        st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG, key="telemetry_mechanical")
