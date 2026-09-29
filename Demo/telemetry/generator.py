"""Reproducible synthetic sensor windows for the interactive demonstration.

Stage targets, fault shapes and tolerances are illustrative assumptions. They
are not a validated engine model, manufacturer limits or maintenance advice.
"""

from numbers import Integral, Real

import numpy as np
import pandas as pd

from Demo.config.engine_specs import stage_reference_bands
from Demo.config.scenarios import FLIGHT_STAGES, SCENARIO_OPTIONS, resolve_scenario


WINDOW_SECONDS = 30
ANOMALY_ONSET_SECONDS = 8
ANOMALY_THRESHOLD = 1.0
EGT_COLUMNS = [f"EGT Cyl {cylinder} (°C)" for cylinder in range(1, 5)]


def _to_frame(signals: dict[str, np.ndarray]) -> pd.DataFrame:
    """Use displayed precision for both scoring and downstream comparisons."""
    df = pd.DataFrame(signals)
    for column in df:
        if column == "Time (s)":
            continue
        df[column] = df[column].round(1 if "RPM" in column or "°C" in column else 2)
    df["EGT Avg (°C)"] = df[EGT_COLUMNS].mean(axis=1).round(1)
    df["EGT Spread (°C)"] = (df[EGT_COLUMNS].max(axis=1) - df[EGT_COLUMNS].min(axis=1)).round(1)
    return df


def score_telemetry(df: pd.DataFrame, flight_stage: str) -> dict:
    """Measure departures from stage reference bands without knowing a fault label.

    A channel score of 1 is one demo tolerance away from its stage target.
    The sample score is the largest channel score. The 95th percentile and
    fraction of samples outside bands determine the illustrative fit score.
    """
    bands = stage_reference_bands(flight_stage)
    missing = set(bands) - set(df.columns)
    if missing:
        raise ValueError(f"Missing telemetry channels: {', '.join(sorted(missing))}")
    if df.empty or not np.isfinite(df[list(bands)].to_numpy(dtype=float)).all():
        raise ValueError("Telemetry must contain finite measurements and at least one sample.")
    channel_scores = pd.DataFrame(
        {
            column: (df[column] - band["nominal"]).abs() / band["tolerance"]
            for column, band in bands.items()
        },
        index=df.index,
    )
    scores = channel_scores.max(axis=1).to_numpy(dtype=float, copy=True)
    # Compare measured values to band edges to avoid floating-point roundoff at
    # an exact boundary (for example abs(3.15 - 3.0) / 0.15).
    outside = pd.DataFrame(
        {
            column: (df[column] < band["min"]) | (df[column] > band["max"])
            for column, band in bands.items()
        },
        index=df.index,
    )
    outlier_mask = outside.any(axis=1).to_numpy(dtype=bool)
    # Keep the documented score threshold and mask equivalent at exact edges.
    scores[~outlier_mask] = np.minimum(scores[~outlier_mask], ANOMALY_THRESHOLD)
    count = int(outlier_mask.sum())
    fraction = float(outlier_mask.mean())
    severity = float(np.percentile(scores, 95))
    health = round(float(np.clip(100 - 12 * max(severity - 0.5, 0) - 35 * fraction, 0, 100)), 1)
    status = "CRITICAL" if count and severity >= 3.0 else "WARNING" if count else "NORMAL"
    color = {"NORMAL": "#3fb950", "WARNING": "#d29922", "CRITICAL": "#f85149"}[status]
    dominant = str(channel_scores.quantile(0.95).idxmax())
    peak_spread = float(df["EGT Spread (°C)"].max())
    if count:
        description = f"{count}/{len(df)} samples outside demo reference bands · strongest departure: {dominant}"
        cluster_text = "REFERENCE DEPARTURE"
        cluster_sub = f"95th-percentile deviation {severity:.2f}× tolerance"
    else:
        description = f"All {len(df)} samples within demo reference bands for {flight_stage.split('. ', 1)[-1]}"
        cluster_text = "WITHIN REFERENCE"
        cluster_sub = f"Peak EGT spread {peak_spread:.1f} °C · no flagged samples"
    return {
        "health": health,
        "rul": None,
        "status_label": status,
        "status_class": f"status-{status.lower()}",
        "status_desc": description,
        "cluster_text": cluster_text,
        "cluster_sub": cluster_sub,
        "cluster_color": color,
        "is_outlier": bool(count),
        "outlier_mask": outlier_mask,
        "anomaly_scores": scores,
        "anomaly_threshold": ANOMALY_THRESHOLD,
        "outlier_count": count,
        "outlier_fraction": fraction,
        "severity_score": severity,
        "dominant_channel": dominant,
        "peak_egt_spread": peak_spread,
        "channel_scores": channel_scores,
        "reference_bands": bands,
    }


def generate_telemetry_data(
    scenario_key: str,
    noise_level: float = 1.0,
    flight_stage: str = "4. Cruise",
    seed: int = 42,
) -> dict:
    """Generate a 30-s window and its matching nominal comparison window.

    ``noise_level`` supports 0–5; zero removes random sensor noise. A local
    generator preserves callers' NumPy random state. ``baseline_df`` shares
    exactly the same nominal noise as ``df``, allowing fair fault comparisons.
    Fault injections begin at sample 8 and develop through the window.
    ``rul`` is retained as None for compatibility: no life prediction is made.
    """
    if not isinstance(flight_stage, str) or flight_stage not in FLIGHT_STAGES:
        raise ValueError(f"Unknown flight stage: {flight_stage!r}")
    if not isinstance(scenario_key, str) or scenario_key not in SCENARIO_OPTIONS:
        raise ValueError(f"Unknown scenario: {scenario_key!r}")
    if isinstance(noise_level, bool) or not isinstance(noise_level, Real) or not np.isfinite(noise_level) or not 0 <= noise_level <= 5:
        raise ValueError("noise_level must be a finite number between 0 and 5.")
    if isinstance(seed, bool) or not isinstance(seed, Integral) or not 0 <= seed <= 2**32 - 1:
        raise ValueError("seed must be an integer between 0 and 4294967295.")

    scenario_key = resolve_scenario(scenario_key, flight_stage)
    rng = np.random.default_rng(int(seed))
    bands = stage_reference_bands(flight_stage)
    t = np.arange(WINDOW_SECONDS)
    fast = np.sin(2 * np.pi * t / 5.0) * 0.3
    slow = np.cos(2 * np.pi * t / 15.0) * 0.5
    waveforms = {
        "Engine RPM": (slow * 25.0, 15.0),
        "EGT Cyl 1 (°C)": (fast * 3.0, 2.0),
        "EGT Cyl 2 (°C)": (slow * 3.0, 2.5),
        "EGT Cyl 3 (°C)": (fast * 2.5, 2.0),
        "EGT Cyl 4 (°C)": (slow * 2.8, 2.2),
        "CHT (°C)": (slow * 1.5, 0.8),
        "MAP (inHg)": (slow * 0.4, 0.25),
        "Fuel Pressure (bar)": (np.zeros(WINDOW_SECONDS), 0.03),
        "Oil Pressure (bar)": (fast * 0.05, 0.04),
        "Vibration (G)": (fast * 0.1, 0.05),
    }
    signals = {"Time (s)": t}
    for channel, (wave, sigma) in waveforms.items():
        signals[channel] = bands[channel]["nominal"] + wave + rng.normal(0, sigma * noise_level, WINDOW_SECONDS)
    baseline = _to_frame(signals)
    observed = {channel: values.copy() for channel, values in signals.items()}
    ramp = np.clip((t - (ANOMALY_ONSET_SECONDS - 1)) / (WINDOW_SECONDS - ANOMALY_ONSET_SECONDS), 0, 1)

    # These scripted perturbations illustrate correlated sensor changes; they
    # do not establish a causal diagnosis or simulate high-frequency dynamics.
    if scenario_key == SCENARIO_OPTIONS[2]:  # Fuel instability
        observed["Fuel Pressure (bar)"] += ramp * (-0.6 + 0.22 * np.sin(t * 1.6))
        observed["EGT Cyl 1 (°C)"] += ramp * 18 * np.sin(t * 1.3)
        observed["EGT Cyl 2 (°C)"] += ramp * 18 * np.cos(t * 1.1)
    elif scenario_key == SCENARIO_OPTIONS[3]:  # Rising temperature
        observed["CHT (°C)"] += ramp * 22
        observed["Oil Pressure (bar)"] -= ramp * 0.6
    elif scenario_key == SCENARIO_OPTIONS[4]:  # Temperature measurement drift
        observed["CHT (°C)"] -= ramp * (bands["CHT (°C)"]["nominal"] - 45.0)
    elif scenario_key == SCENARIO_OPTIONS[5]:  # Increasing vibration magnitude
        observed["Vibration (G)"] += ramp * (1.4 + 0.15 * np.sin(t * 1.9))
    elif scenario_key == SCENARIO_OPTIONS[6]:  # Cylinder imbalance
        observed["EGT Cyl 2 (°C)"] += ramp * 85
    elif scenario_key == SCENARIO_OPTIONS[7]:  # Loss of oil pressure
        observed["Oil Pressure (bar)"] -= ramp * (bands["Oil Pressure (bar)"]["nominal"] - 1.1)
        observed["CHT (°C)"] += ramp * 14
        observed["Vibration (G)"] += ramp * 0.8
    elif scenario_key == SCENARIO_OPTIONS[8]:  # Manifold pressure departure
        observed["MAP (inHg)"] -= ramp * 10
        observed["Engine RPM"] -= ramp * 600

    df = _to_frame(observed)
    for frame in (df, baseline):
        frame.attrs.update(reference_bands=stage_reference_bands(flight_stage), flight_stage=flight_stage, anomaly_threshold=ANOMALY_THRESHOLD)
    return {
        "df": df,
        "baseline_df": baseline,
        "scenario_key": scenario_key,
        "flight_stage": flight_stage,
        "seed": int(seed),
        "noise_level": float(noise_level),
        "anomaly_onset": ANOMALY_ONSET_SECONDS,
        **score_telemetry(df, flight_stage),
    }
