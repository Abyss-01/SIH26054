"""Shared choices and deterministic stage routing for the synthetic demo."""

import math
from numbers import Real


AUTO_SCENARIO = "Auto (Follow Flight Profile Stages)"
NOMINAL_SCENARIO = "Nominal Operation (No Anomaly)"
SCENARIO_OPTIONS = (
    AUTO_SCENARIO,
    NOMINAL_SCENARIO,
    "1. Fuel Pressure Anomaly (2.5 - 3.5 bar instability)",
    "2. Cooling Degradation / Thermal Overheating",
    "3. Coolant Sensor Drift / False-Low Reading",
    "4. Gearbox High-Frequency Vibration Anomaly",
    "5. EGT Cylinder 2 Combustion Imbalance",
    "6. Oil Pressure Loss / Lubrication Degradation",
    "7. Turbocharger Boost Air-Path Collapse",
)
SCENARIO_LABELS = dict(zip(SCENARIO_OPTIONS, (
    "Guided flight tour",
    "Nominal operation",
    "Fuel pressure instability",
    "Cooling degradation",
    "Temperature sensor drift",
    "Elevated vibration",
    "Cylinder 2 EGT imbalance",
    "Oil pressure loss",
    "Boost pressure loss",
)))
FLIGHT_STAGES = (
    "1. Warm-Up (ground)",
    "2. Take-Off",
    "3. Climb",
    "4. Cruise",
    "5. Loiter / Endurance",
    "6. Descent / Return",
    "7. Landing / Cooldown",
)
_STAGE_ENDS = (20, 50, 110, 180, 240, 280, 300)
_AUTO_TOUR = dict(zip(FLIGHT_STAGES, (
    NOMINAL_SCENARIO,
    NOMINAL_SCENARIO,
    SCENARIO_OPTIONS[3],
    SCENARIO_OPTIONS[2],
    SCENARIO_OPTIONS[5],
    SCENARIO_OPTIONS[8],
    SCENARIO_OPTIONS[7],
)))


def stage_at_distance(distance: float) -> str:
    """Map 0–300 km of illustrative mission progress onto the seven stages."""
    if isinstance(distance, bool) or not isinstance(distance, Real) or not math.isfinite(distance) or not 0 <= distance <= 300:
        raise ValueError("Mission distance must be a finite number between 0 and 300 km.")
    return next(stage for stage, end in zip(FLIGHT_STAGES, _STAGE_ENDS) if distance <= end)


def resolve_scenario(manual_scenario: str, flight_stage: str) -> str:
    """Keep manual selection, or select a repeatable fault for the stage tour."""
    if not isinstance(manual_scenario, str) or manual_scenario not in SCENARIO_OPTIONS:
        raise ValueError(f"Unknown scenario: {manual_scenario!r}")
    if not isinstance(flight_stage, str) or flight_stage not in FLIGHT_STAGES:
        raise ValueError(f"Unknown flight stage: {flight_stage!r}")
    return _AUTO_TOUR[flight_stage] if manual_scenario == AUTO_SCENARIO else manual_scenario
