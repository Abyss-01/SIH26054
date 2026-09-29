"""Pydantic models for the AERIS snapshot API."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Scenario(str, Enum):
    """All scenario keys accepted by the engine."""

    AUTO = "Auto (Follow Flight Profile Stages)"
    NOMINAL = "Nominal Operation (No Anomaly)"
    FUEL_PRESSURE = "1. Fuel Pressure Anomaly (2.5 - 3.5 bar instability)"
    COOLING_DEGRADATION = "2. Cooling Degradation / Thermal Overheating"
    SENSOR_DRIFT = "3. Coolant Sensor Drift / False-Low Reading"
    GEARBOX_VIBRATION = "4. Gearbox High-Frequency Vibration Anomaly"
    EGT_IMBALANCE = "5. EGT Cylinder 2 Combustion Imbalance"
    OIL_PRESSURE_LOSS = "6. Oil Pressure Loss / Lubrication Degradation"
    TURBO_AIR_PATH = "7. Turbocharger Boost Air-Path Collapse"


class SnapshotRequest(BaseModel):
    scenario: Scenario = Field(..., description="Scenario key (or Auto for the guided tour).")
    noise_level: float = Field(ge=0.0, le=5.0, description="Sensor noise multiplier (0 = silent).")
    sample_seed: int = Field(ge=0, le=2**32 - 1, description="Reproducible RNG seed.")
    flight_distance: float = Field(ge=0.0, le=300.0, description="Mission distance in km (0-300).")


class ReferenceBand(BaseModel):
    nominal: float
    min: float
    max: float
    tolerance: float
    unit: str


class SnapshotResponse(BaseModel):
    """Full telemetry snapshot, shaped for the React dashboard."""

    meta: Dict[str, Any] = Field(..., description="Scenario / stage / distance / run identity.")
    health: Dict[str, Any] = Field(..., description="Score, status label, description.")
    cluster: Dict[str, Any] = Field(..., description="Cluster classification text/colour.")
    channels: Dict[str, Any] = Field(
        ..., description="Column names and per-sample records for observed + baseline."
    )
    anomaly: Dict[str, Any] = Field(..., description="Per-sample scores, mask, threshold, aggregate.")
    reference_bands: Dict[str, ReferenceBand] = Field(..., description="Per-channel demo reference bands.")
    rul: Optional[float] = Field(None, description="Remaining useful life (always null for this demo).")
