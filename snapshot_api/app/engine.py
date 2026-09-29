"""Integration with the existing SIH26054 Demo engine.

The snapshot API delegates to the unmodified Demo telemetry generator so the
existing simulation tests keep meaning and the React frontend receives the same
data shape the Streamlit console already produces.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd
import numpy as np

from Demo.telemetry.generator import generate_telemetry_data, ANOMALY_ONSET_SECONDS
from Demo.config.scenarios import SCENARIO_OPTIONS, stage_at_distance

# ---------------------------------------------------------------------------
# JSON serialisation helpers
# ---------------------------------------------------------------------------

def _native(obj: Any) -> Any:
    """Recursively convert numpy scalars / arrays to JSON-safe Python types."""
    if obj is None:
        return None
    if isinstance(obj, (list, tuple)):
        return [_native(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _native(v) for k, v in obj.items()}
    if isinstance(obj, np.ndarray):
        return _native(obj.tolist())
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return None if pd.isna(obj) else float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()
    return obj


def records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Observed / baseline DataFrame → list of per-sample records."""
    if df is None or df.empty:
        return []
    return _native(df.to_dict(orient="records"))


def reference_bands(bands: Dict[str, Dict]) -> Dict[str, Any]:
    """Ensure reference-band values are plain Python types for JSON."""
    return {
        channel: {
            "nominal": float(band["nominal"]),
            "min": float(band["min"]),
            "max": float(band["max"]),
            "tolerance": float(band["tolerance"]),
            "unit": str(band["unit"]),
        }
        for channel, band in bands.items()
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_snapshot(
    scenario: str,
    noise_level: float,
    sample_seed: int,
    flight_distance: float,
) -> Dict[str, Any]:
    """Generate a 30-second telemetry window and shape it for the dashboard."""
    # Resolve the flight stage from mission distance, then delegate to the engine.
    flight_stage = stage_at_distance(flight_distance)
    result = generate_telemetry_data(
        scenario_key=scenario,
        noise_level=noise_level,
        flight_stage=flight_stage,
        seed=sample_seed,
    )

    df = result["df"]
    baseline_df = result.get("baseline_df")

    channels = {
        "columns": list(df.columns),
        "observed": records(df),
        "baseline": records(baseline_df),
    }

    return {
        "meta": {
            "scenario": result["scenario_key"],
            "requested_scenario": scenario,
            "flight_stage": result["flight_stage"],
            "flight_distance_km": flight_distance,
            "noise_level": noise_level,
            "seed": sample_seed,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "anomaly_onset": int(ANOMALY_ONSET_SECONDS),
        },
        "health": {
            "score": float(result["health"]),
            "status": str(result["status_label"]),
            "status_class": str(result["status_class"]),
            "description": str(result["status_desc"]),
            "outlier_count": int(result["outlier_count"]),
            "outlier_fraction": float(result["outlier_fraction"]),
            "severity": float(result["severity_score"]),
            "dominant_channel": str(result["dominant_channel"]),
            "peak_egt_spread": float(result["peak_egt_spread"]),
        },
        "cluster": {
            "text": str(result["cluster_text"]),
            "sub": str(result["cluster_sub"]),
            "color": str(result["cluster_color"]),
        },
        "channels": channels,
        "anomaly": {
            "scores": _native(result["anomaly_scores"]),
            "mask": _native(result["outlier_mask"]),
            "threshold": float(result["anomaly_threshold"]),
        },
        "reference_bands": reference_bands(result["reference_bands"]),
        "rul": None,
    }


def available_scenarios() -> List[str]:
    """All scenario keys the engine accepts, including Auto."""
    return list(SCENARIO_OPTIONS)
