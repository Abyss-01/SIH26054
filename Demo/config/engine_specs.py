"""Illustrative stage targets and demo reference bands, not OEM limits.

These numbers support a synthetic presentation and have not been validated
against a specific aircraft installation or engine maintenance manual.
"""

from Demo.config.scenarios import FLIGHT_STAGES


# Preserved for compatibility. Prefer stage_reference_bands in new displays.
ENGINE_SPECS = {
    "RPM": {"min": 1800, "max": 5800, "nominal": 5400, "unit": "RPM"},
    "EGT": {"min": 750, "max": 950, "nominal": 800, "unit": "°C"},
    "CHT": {"min": 100, "max": 120, "nominal": 110, "unit": "°C"},
    "MAP": {"min": 30, "max": 45, "nominal": 40, "unit": "inHg"},
    "Fuel_Pressure": {"min": 2.9, "max": 3.2, "nominal": 3.0, "unit": "bar"},
    "Oil_Pressure": {"min": 2.0, "max": 5.0, "nominal": 4.0, "unit": "bar"},
    "Vibration": {"min": 1.5, "max": 2.5, "nominal": 2.0, "unit": "G"},
}

# RPM, EGT, CHT, MAP, fuel pressure, oil pressure, vibration magnitude.
_STAGE_TARGETS = {
    FLIGHT_STAGES[0]: (2200.0, 760.0, 65.0, 30.0, 3.0, 4.8, 1.6),
    FLIGHT_STAGES[1]: (5800.0, 850.0, 115.0, 44.5, 3.1, 4.2, 2.2),
    FLIGHT_STAGES[2]: (5600.0, 835.0, 112.0, 42.0, 3.05, 4.1, 2.1),
    FLIGHT_STAGES[3]: (5400.0, 800.0, 108.0, 40.0, 3.0, 4.0, 2.0),
    FLIGHT_STAGES[4]: (4900.0, 780.0, 102.0, 36.0, 3.0, 3.9, 1.8),
    FLIGHT_STAGES[5]: (3900.0, 760.0, 98.0, 32.0, 2.95, 3.8, 1.7),
    FLIGHT_STAGES[6]: (2000.0, 740.0, 90.0, 29.0, 2.95, 3.7, 1.5),
}


def stage_reference_bands(flight_stage: str) -> dict[str, dict]:
    """Return independent per-channel nominal targets and scoring tolerances."""
    if not isinstance(flight_stage, str) or flight_stage not in _STAGE_TARGETS:
        raise ValueError(f"Unknown flight stage: {flight_stage!r}")
    rpm, egt, cht, manifold, fuel, oil, vibration = _STAGE_TARGETS[flight_stage]
    channels = {
        "Engine RPM": (rpm, 150.0, "RPM"),
        "EGT Cyl 1 (°C)": (egt - 2, 25.0, "°C"),
        "EGT Cyl 2 (°C)": (egt + 2, 25.0, "°C"),
        "EGT Cyl 3 (°C)": (egt - 5, 25.0, "°C"),
        "EGT Cyl 4 (°C)": (egt + 5, 25.0, "°C"),
        "EGT Avg (°C)": (egt, 25.0, "°C"),
        "CHT (°C)": (cht, 8.0, "°C"),
        "MAP (inHg)": (manifold, 2.0, "inHg"),
        "Fuel Pressure (bar)": (fuel, 0.15, "bar"),
        "Oil Pressure (bar)": (oil, 0.5, "bar"),
        "Vibration (G)": (vibration, 0.4, "G"),
        "EGT Spread (°C)": (10.0, 35.0, "°C"),
    }
    return {
        channel: {
            "nominal": target,
            "min": max(0.0, round(target - tolerance, 6)),
            "max": round(target + tolerance, 6),
            "tolerance": tolerance,
            "unit": unit,
        }
        for channel, (target, tolerance, unit) in channels.items()
    }
