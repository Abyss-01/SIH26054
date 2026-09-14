# simulation — ROTAX 915 Digital Twin Engine Simulator
#
# Physics-based engine simulator for the SIH26054 project.
# Generates real-time telemetry for the digital twin and ML layers.
#
# Evidence policy (from engine-baseline.md):
#   SOURCE   — directly from BRP-Rotax manuals
#   DERIVED  — calculated from source-backed values
#   ASSUMPTION — engineering judgement where manuals are silent
#   TBD      — not yet defined
#
# NOTE: This simulator targets the ROTAX 915 i A / C24 baseline documented in
# docs/engine-baseline.md. The SIH problem statement references the 915 iS series.
# Differences between 915 i A/C24 and 915 iS are TBD until the correct manual set
# is obtained. Do not present ASSUMPTION values as manufacturer specifications.

import json
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional, List, Dict
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class OperatingMode(Enum):
    ECO = "ECO"
    POWER = "POWER"


class MissionPhase(Enum):
    START = "start"
    TAKEOFF = "takeoff"
    CLIMB = "climb"
    CRUISE = "cruise"
    HIGH_LOAD = "high_load"
    DESCENT = "descent"
    LANDING = "landing"


# ---------------------------------------------------------------------------
# State dataclass
# ---------------------------------------------------------------------------

@dataclass
class EngineState:
    """Full state vector for one simulation step."""

    # --- Primary inputs / commands ---
    time: float = 0.0
    rpm: float = 1800.0
    throttle_position: float = 0.0
    ambient_pressure: float = 1013.0       # hPa  (SOURCE: OM 2.1)
    ambient_temperature: float = 25.0       # °C   (SOURCE: OM 2.1)
    altitude: float = 0.0                   # ft   (ASSUMPTION for mission profile)

    # --- Air path ---
    airflow: float = 0.0                    # kg/s (ASSUMPTION — Display CAN availability TBD)
    manifold_pressure: float = 125.0         # mbar (SOURCE: MAPS 1/2, OM 2.1)
    manifold_temperature: float = 25.0      # °C   (SOURCE: MATS 1/2)
    boost_pressure: float = 0.0             # mbar above ambient (SOURCE: BPS, OM 7.6)

    # --- Lubrication ---
    oil_pressure: float = 2.0               # bar  (SOURCE: OM 2.1)
    oil_temperature: float = 25.0           # °C   (SOURCE: OTS, OM 2.1)

    # --- Cooling ---
    coolant_temperature: float = 25.0       # °C   (SOURCE: CTS, OM 2.1)

    # --- Exhaust ---
    egt_1: float = 25.0                     # °C   (SOURCE: EGT 1-4, MMH)
    egt_2: float = 25.0                     # °C
    egt_3: float = 25.0                     # °C
    egt_4: float = 25.0                     # °C

    # --- Fuel ---
    fuel_pressure: float = 3.0              # bar  (SOURCE: OM 2.1)

    # --- EMS / CAN / Electrical ---
    lane_a_state: str = "ACTIVE"            # SOURCE: dual-lane EMS (OM 7.5.1)
    lane_b_state: str = "ACTIVE"
    display_can_a_state: str = "ACTIVE"     # SOURCE: dual Display CAN (IM 77-00-00)
    display_can_b_state: str = "ACTIVE"
    generator_state: str = "GEN2"           # SOURCE: OM 7.5 (GEN2 at start, GEN1 takes over)

    # --- Derived / computed ---
    operating_mode: str = "ECO"             # SOURCE: OM 5.3 (~97% throttle threshold)
    egt_split: float = 0.0                  # DERIVED: max(EGT) - min(EGT)  (SOURCE formula)
    expected_power: float = 0.0             # kW   (DERIVED from SOURCE power limits)
    expected_fuel_flow: float = 0.0         # L/h  (DERIVED from OM 5.1-5.2 model inputs)
    health_score: float = 100.0             # 0-100 (project metric, ASSUMPTION scale)
    vibration_rms: float = 0.0              # g    (ASSUMPTION — no source amplitude available)


# ---------------------------------------------------------------------------
# Fault configuration
# ---------------------------------------------------------------------------

@dataclass
class FaultConfig:
    """Effective fault amplitudes for the current sample (all normalized).
    Event schedules live separately so repeated injections retain their timing.
    """
    active: bool = False
    oil_degradation: float = 0.0
    coolant_leak: float = 0.0
    fuel_filter_clog: float = 0.0
    injector_degradation: float = 0.0
    bearing_wear: float = 0.0
    sensor_drift: float = 0.0


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------

class Rotax915Simulator:
    """
    Physics-based simulator for the ROTAX 915 series.

    Every numerical value traces to one of: SOURCE / DERIVED / ASSUMPTION / TBD.
    See engine-baseline.md for the full evidence chain.

    This implementation covers the MVP scope from architecture.md:
      - One representative engine model
      - Real-time sensor data across mission phases
      - Basic fault injection
      - Digital-twin residual-ready outputs
      - Health score and derived features for ML
    """

    # =========================================================================
    # SOURCE-backed operating limits (engine-baseline.md, OM 2.1)
    # =========================================================================

    RPM_IDLE_MIN = 1800.0                  # rpm  (SOURCE: OM 2.1, p. 2-2)
    RPM_MAX = 5800.0                       # rpm  (SOURCE: OM 2.1, p. 2-2, max 5 min)
    RPM_CONTINUOUS = 5500.0                # rpm  (SOURCE: OM 2.1, p. 2-2)
    POWER_TAKEOFF = 104.0                  # kW   (SOURCE: OM 2.1, p. 2-2, @ 5800 rpm)
    POWER_CONTINUOUS = 99.0                # kW   (SOURCE: OM 2.1, p. 2-2, @ 5500 rpm)
    ALTITUDE_CRITICAL = 15000.0            # ft   (SOURCE: OM 2.1, p. 2-2, MAT <= 50°C)
    ALTITUDE_MAX = 23000.0                 # ft   (SOURCE: OM 2.1, p. 2-3)

    # Oil pressure (SOURCE: OM 2.1, p. 2-4)
    OIL_PRESSURE_NORMAL_MIN = 2.0          # bar  (>3500 rpm)
    OIL_PRESSURE_NORMAL_MAX = 5.0          # bar
    OIL_PRESSURE_MIN_LOW_RPM = 0.8         # bar  (<3500 rpm)
    OIL_PRESSURE_MAX_COLD = 7.0            # bar  (cold start / warm-up)

    # Oil temperature (SOURCE: OM 2.1, p. 2-5)
    OIL_TEMP_START_MIN = -20.0             # °C
    OIL_TEMP_PRE_TAKEOFF = 50.0            # °C  (must reach before takeoff)
    OIL_TEMP_NORMAL_MIN = 50.0             # °C
    OIL_TEMP_NORMAL_MAX = 130.0            # °C

    # Coolant temperature (SOURCE: OM 2.1, p. 2-5; CTS in cyl head of cyl 4 per MMH)
    COOLANT_TEMP_MAX = 120.0               # °C  (normal-operation max)

    # EGT (SOURCE: OM 2.1, p. 2-5/2-6)
    EGT_MAX = 950.0                        # °C
    EGT_SPLIT_MAX_HIGH_FUEL = 200.0        # °C  (fuel > 3 L/h)
    EGT_SPLIT_MAX_LOW_FUEL = 500.0         # °C  (fuel < 3 L/h)

    # Fuel pressure (SOURCE: OM 2.1, p. 2-6)
    FUEL_PRESSURE_NORMAL_MIN = 2.9         # bar
    FUEL_PRESSURE_NORMAL_MAX = 3.2         # bar
    FUEL_PRESSURE_EXCURSION_MIN = 2.5      # bar  (max 3 s after power change)
    FUEL_PRESSURE_EXCURSION_MAX = 3.5      # bar

    # Manifold pressure targets (SOURCE: OM 2.1, p. 2-4)
    MAP_TARGET_5800 = 1520.0               # mbar @ 5800 rpm, 25-35°C
    MAP_TARGET_5500 = 1450.0               # mbar @ 5500 rpm, 25-35°C
    MAP_MIN = 60.0                         # hPa
    MAP_MAX = 1730.0                       # hPa

    # Manifold air temperature (SOURCE: OM 2.1, p. 2-3)
    MAT_MAX_NORMAL = 50.0                  # °C
    MAT_EXTENDED_MAX = 80.0                # °C  (>50°C, reduced power)

    # Ambient (SOURCE: OM 2.1, p. 2-6)
    AMBIENT_TEMP_MIN = -40.0               # °C
    AMBIENT_TEMP_MAX = 50.0                # °C

    # ECO/POWER mode threshold (SOURCE: OM 5.3, p. 5-7)
    ECO_THRESHOLD = 0.97                   # throttle fraction

    # =========================================================================
    # ASSUMPTION-based model parameters (no source value available)
    # =========================================================================

    # Thermal time constants (ASSUMPTION — no source data)
    OIL_THERMAL_TC = 120.0                 # seconds (ASSUMPTION)
    COOLANT_THERMAL_TC = 180.0             # seconds (ASSUMPTION)

    # Vibration (ASSUMPTION — no healthy amplitude published)
    VIBRATION_RMS_HEALTHY_BASE = 0.05      # g    (ASSUMPTION, normalized)
    VIBRATION_FAULT_PER_SEVERITY = 0.5     # g per unit severity (ASSUMPTION)

    # EGT nominal setpoints by phase (ASSUMPTION — no source values per phase)
    EGT_NOMINAL_BY_PHASE = {
        MissionPhase.START:     200.0,     # °C  (ASSUMPTION — cold engine)
        MissionPhase.TAKEOFF:   760.0,     # °C  (ASSUMPTION — high power, near limit)
        MissionPhase.CLIMB:     700.0,     # °C  (ASSUMPTION)
        MissionPhase.CRUISE:    620.0,     # °C  (ASSUMPTION — ECO mode typical)
        MissionPhase.HIGH_LOAD: 800.0,     # °C  (ASSUMPTION — near EGT_MAX)
        MissionPhase.DESCENT:   380.0,     # °C  (ASSUMPTION — reducing power)
        MissionPhase.LANDING:   280.0,     # °C  (ASSUMPTION — cooldown)
    }

    # Per-cylinder EGT variation (ASSUMPTION — no source spread data)
    EGT_PER_CYL_VAR = 15.0                 # °C RMS (ASSUMPTION)

    # Fuel flow model (ASSUMPTION — shape from OM 5.1-5.2, scale TBD)
    FUEL_FLOW_IDLE = 1.5                   # L/h  (ASSUMPTION — idle burn)
    FUEL_DENSITY_KG_L = 0.745              # ASSUMPTION: gasoline density
    BSFC_ECO = 0.270                      # kg/kWh, ASSUMPTION, uncalibrated
    BSFC_POWER = 0.300                    # kg/kWh, ASSUMPTION, enrichment

    # Airflow model (SOURCE displacement, ASSUMPTION volumetric efficiency)
    ESTIMATED_DISPLACEMENT_L = 1.352       # L    (SOURCE — 915 total displacement, 1.352 L)
    VOLUMETRIC_EFFICIENCY = 0.80           # —    (ASSUMPTION)

    # Mission profile transition smoothing (ASSUMPTION)
    PHASE_TRANSITION_TC = 5.0              # seconds (ASSUMPTION)

    ALTITUDE_TEMP_LAPSE = -0.0065          # °C/m (ASSUMPTION — standard lapse rate)

    # =========================================================================
    # Constructor
    # =========================================================================

    def __init__(self, dt: float = 1.0, duration: float = 3600.0, seed: int | None = None):
        """
        Args:
            dt:        Time step in seconds (default 1.0 → 1 Hz telemetry)
            duration:  Total simulation duration in seconds
        """
        if not np.isfinite(dt) or dt <= 0 or not np.isfinite(duration) or duration <= 0:
            raise ValueError("dt and duration must be finite and positive")
        self.rng = np.random.default_rng(seed)
        self._events = []
        self._egt_biases = np.zeros(4)
        self.dt = dt
        self.duration = duration
        self.time = 0.0
        self.state = EngineState()
        self.mission_profile: List[Dict] = []
        self.fault = FaultConfig()
        self.vibration_rms = 0.0
        self.history: List[Dict] = []
        self._current_phase_idx = 0

        # Phase target tracking (for smooth transitions)
        self._phase_target_rpm: float = 1800.0
        self._phase_target_throttle: float = 0.0
        self._phase_target_altitude: float = 0.0
        self._phase_ambient_temp: float = 25.0
        self._phase_ambient_pressure: float = 1013.0
        self._phase_duration_remaining: float = 0.0

    # =========================================================================
    # Mission profile
    # =========================================================================

    def set_mission_profile(self, phases: List[Dict]):
        """
        Define the mission profile as a list of phase dicts.

        Each dict:
            phase:            MissionPhase value (str OK)
            duration:         seconds
            target_rpm:       rpm  (ASSUMPTION — aircraft-specific schedule)
            target_throttle:  0.0-1.0 fraction (ASSUMPTION)
            target_altitude:  ft   (ASSUMPTION)
            ambient_temp:     °C   (optional, defaults to 25°C)
            ambient_pressure: hPa  (optional, auto-computed from altitude if omitted)

        RPM and throttle follow a first-order lag. Altitude moves linearly
        from the previous endpoint to this endpoint over the phase duration.
        ambient_temp is a sea-level reference, not the local temperature.
        """
        if not phases:
            raise ValueError("mission profile must contain at least one phase")
        for phase in phases:
            MissionPhase(phase['phase'])
            for key in ('duration', 'target_rpm', 'target_throttle', 'target_altitude'):
                if not np.isfinite(phase[key]):
                    raise ValueError(f"{key} must be finite")
            if phase['duration'] <= 0:
                raise ValueError("phase durations must be positive")
            if not self.RPM_IDLE_MIN <= phase['target_rpm'] <= self.RPM_MAX:
                raise ValueError("target RPM outside model range")
            if not 0 <= phase['target_throttle'] <= 1 or not 0 <= phase['target_altitude'] <= self.ALTITUDE_MAX:
                raise ValueError("invalid throttle or altitude")
        self.mission_profile = [dict(p) for p in phases]
        self._current_phase_idx = 0
        self._load_phase(0)

    def _load_phase(self, index: int):
        if index >= len(self.mission_profile):
            return
        p = self.mission_profile[index]
        self._phase_duration_remaining = float(p['duration'])
        self._phase_target_rpm = float(p['target_rpm'])
        self._phase_target_throttle = float(p['target_throttle'])
        self._phase_target_altitude = float(p['target_altitude'])
        self._phase_ambient_temp = float(p.get('ambient_temp', 25.0))
        self._phase_ambient_pressure = float(p.get(
            'ambient_pressure',
            self._altitude_to_pressure(self._phase_target_altitude)
        ))

    def _advance_phase(self):
        self._current_phase_idx += 1
        if self._current_phase_idx < len(self.mission_profile):
            self._load_phase(self._current_phase_idx)
        # else: stay at last phase targets (simulation holds)

    def _altitude_to_pressure(self, altitude_ft: float) -> float:
        """Tropospheric standard-atmosphere approximation; altitude input is feet."""
        h_m = float(np.clip(altitude_ft, 0.0, self.ALTITUDE_MAX)) * 0.3048
        return 1013.25 * (1.0 - 2.2557e-5 * h_m) ** 5.2558

    def _altitude_to_temperature(self, altitude_ft: float, sea_level_temp: float) -> float:
        """Approximate ambient temperature at altitude (ASSUMPTION — standard lapse)."""
        altitude_m = altitude_ft * 0.3048
        return sea_level_temp + self.ALTITUDE_TEMP_LAPSE * altitude_m

    # =========================================================================
    # Main step
    # =========================================================================

    def step(self) -> Dict:
        """
        Advance one time step and return a snapshot dict suitable for CSV.
        """
        # Samples describe the state at the end of this time interval.
        self.time += self.dt

        # --- Mission phase advancement ---
        self._update_mission_phase()

        # --- Gate fault params by their individual onset times ---
        # Each fault parameter is multiplied by a 0→1 ramp that starts at its
        # own onset_time. This lets combined scenarios have faults activate at
        # different times, and lets gradual scenarios ramp up smoothly.
        self._gate_faults_by_onset()

        # --- Operating mode ---
        self._compute_operating_mode()

        # --- Physics chain ---
        self._compute_manifold_pressure()
        self._compute_boost_pressure()
        self._compute_manifold_temperature()
        self._compute_airflow()
        self._compute_oil_pressure()
        self._compute_oil_temperature()
        self._compute_coolant_temperature()
        self._compute_egt()
        self._compute_egt_split()
        self._compute_expected_power()
        self._compute_fuel_flow()
        self._compute_fuel_pressure()
        self._compute_vibration()
        self.state.health_score = self._compute_health_score()
        self._update_lane_can_state()

        # --- Record ---
        snapshot = self._make_snapshot()
        self.history.append(snapshot)
        return snapshot

    # =========================================================================
    # Fault onset gating
    # =========================================================================

    def _gate_faults_by_onset(self):
        """Apply independently timed events. Active windows are [onset, end).
        Severity ramps over 60 s, reaches the configured value, then switches
        off at event expiry. Thermal state can retain a physical recovery lag.
        """
        for name in ('oil_degradation', 'coolant_leak', 'fuel_filter_clog',
                     'injector_degradation', 'bearing_wear', 'sensor_drift'):
            setattr(self.fault, name, 0.0)
        self._egt_biases[:] = 0.0
        for event in self._events:
            if not event['onset'] <= self.time < event['onset'] + event['duration']:
                continue
            progress = min(1.0, (self.time - event['onset']) / 60.0)
            severity = event['severity'] * progress ** 2 * (3 - 2 * progress)
            if event['type'] == 'egt_sensor_fault':
                idx = event['sensor_id'] - 1
                self._egt_biases[idx] = max(self._egt_biases[idx], 75.0 * severity)
            else:
                name = event['type']
                setattr(self.fault, name, max(getattr(self.fault, name), severity))

    def _update_mission_phase(self):
        """Integrate commands across phase boundaries; altitude reaches its endpoint
        over the phase duration, rather than using the engine's five-second lag.
        Ambient temperature inputs are sea-level reference temperatures.
        """
        if not self.mission_profile:
            return
        interval_start = self.time - self.dt
        phase_start = 0.0
        start_altitude = 0.0
        for idx, phase in enumerate(self.mission_profile):
            phase_end = phase_start + phase['duration']
            overlap = min(self.time, phase_end) - max(interval_start, phase_start)
            if overlap > 0:
                self._current_phase_idx = idx
                alpha = -np.expm1(-overlap / self.PHASE_TRANSITION_TC)
                self.state.rpm += alpha * (phase['target_rpm'] - self.state.rpm)
                self.state.throttle_position += alpha * (phase['target_throttle'] - self.state.throttle_position)
                progress = (min(self.time, phase_end) - phase_start) / phase['duration']
                self.state.altitude = start_altitude + progress * (phase['target_altitude'] - start_altitude)
                self.state.ambient_temperature = self._altitude_to_temperature(
                    self.state.altitude, phase.get('ambient_temp', 25.0))
                self.state.ambient_pressure = phase.get('ambient_pressure', self._altitude_to_pressure(self.state.altitude))
            phase_start = phase_end
            start_altitude = phase['target_altitude']
        # A caller stepping beyond the profile explicitly holds the final state.
        # The dataset generator requires mission duration == run duration.

    # =========================================================================
    # Physics models
    # =========================================================================

    def _compute_operating_mode(self):
        """ECO vs POWER (SOURCE: OM 5.3, ~97% throttle threshold)."""
        if self.state.throttle_position >= self.ECO_THRESHOLD or \
           self.state.lane_b_state != "ACTIVE" or self.state.lane_a_state != "ACTIVE":
            self.state.operating_mode = OperatingMode.POWER.value
        else:
            self.state.operating_mode = OperatingMode.ECO.value

    def _compute_manifold_pressure(self):
        """
        Manifold pressure from throttle position and RPM.

        SOURCE anchors: MAP target 1520 mbar @ 5800 rpm, 1450 mbar @ 5500 rpm
        (OM 2.1, p. 2-4, 25-35°C).

        ASSUMPTION: below 5500 rpm, target MAP scales approximately linearly with
        RPM. Throttle position scales actual MAP between idle (low) and full-throttle
        (near target). Idle MAP is ASSUMED at ~30% of target.
        """
        rpm = self.state.rpm

        # Target MAP by RPM (SOURCE at 5500/5800, ASSUMPTION elsewhere)
        if rpm >= 5800:
            target_map = self.MAP_TARGET_5800
        elif rpm >= 5500:
            frac = (rpm - 5500.0) / 300.0
            target_map = self.MAP_TARGET_5500 + frac * (self.MAP_TARGET_5800 - self.MAP_TARGET_5500)
        elif rpm >= self.RPM_IDLE_MIN:
            # Below 5500: linear ramp from idle MAP target up to 5500 target (ASSUMPTION)
            idle_map_target = self.MAP_TARGET_5500 * 0.3  # ASSUMPTION: idle target ~30% of cruise
            frac = (rpm - self.RPM_IDLE_MIN) / (5500.0 - self.RPM_IDLE_MIN)
            target_map = idle_map_target + frac * (self.MAP_TARGET_5500 - idle_map_target)
        else:
            target_map = self.MAP_TARGET_5500 * 0.3

        target_map = np.clip(target_map, self.MAP_MIN, self.MAP_MAX)

        # Throttle controls how close to target we get
        # At very low throttle, MAP is low (engine drawing air, not boosted)
        # At full throttle, MAP approaches target (turbocharged)
        throttle_factor = 0.25 + 0.75 * self.state.throttle_position  # ASSUMPTION

        self.state.manifold_pressure = target_map * throttle_factor
        self.state.manifold_pressure = np.clip(
            self.state.manifold_pressure, self.MAP_MIN, self.MAP_MAX
        )

    def _compute_boost_pressure(self):
        """
        Boost = manifold pressure above ambient.

        SOURCE: turbocharger + wastegate + overboost valve (OM 7.6, p. 7-19).
        DERIVED: boost_pressure = manifold_pressure - ambient_pressure.
        """
        self.state.boost_pressure = max(
            0.0, self.state.manifold_pressure - self.state.ambient_pressure
        )

    def _compute_manifold_temperature(self):
        """Ideal-gas compressor heating with assumed efficiencies.
        Approximate compressor outlet pressure by manifold pressure; at idle
        the throttle vacuum is not treated as compressor expansion cooling.
        Compressor efficiency 0.72, intercooler effectiveness 0.70 and intake
        heat soak +2 C are uncalibrated assumptions. Limits remain diagnostic.
        """
        ambient_k = self.state.ambient_temperature + 273.15
        ratio = max(1.0, self.state.manifold_pressure / self.state.ambient_pressure)
        compression_rise = ambient_k * (ratio ** (2.0 / 7.0) - 1.0) / 0.72
        self.state.manifold_temperature = self.state.ambient_temperature + 2.0 + 0.30 * compression_rise

    def _compute_airflow(self):
        """
        Estimated airflow mass flow.

        SOURCE: airflow is available on Display CAN (OM 2.1, p. 2-3).
        ASSUMPTION: estimated from RPM, manifold pressure, temperature using
        ideal gas law and estimated displacement.

        NOTE: This is an ESTIMATE. The actual Display CAN airflow value is
        SOURCE-available but the parameter dictionary is TBD. Do not claim
        this estimate equals the ECU's reported airflow.
        """
        # Air density in manifold (ideal gas law)
        manifold_mbar = self.state.manifold_pressure
        manifold_temp_c = self.state.manifold_temperature
        manifold_temp_k = manifold_temp_c + 273.15
        density = manifold_mbar * 100.0 / (manifold_temp_k * 287.0)  # Pa / (J/kg/K * K)

        # Total displacement; one intake stroke per two crankshaft revolutions
        displacement_m3 = self.ESTIMATED_DISPLACEMENT_L * 1e-3
        airflow = density * displacement_m3 * (self.state.rpm / 120.0) * \
                  self.VOLUMETRIC_EFFICIENCY

        self.state.airflow = max(0.0, airflow)  # kg/s

    def _compute_oil_pressure(self):
        """
        Oil pressure from RPM and thermal state.

        SOURCE: 2.0-5.0 bar normal (>3500 rpm), 0.8 bar min (<3500 rpm),
        7.0 bar max cold start (OM 2.1, p. 2-4).

        ASSUMPTION: pressure rises with RPM; cold oil (thick) gives higher
        pressure at startup, tapering as oil warms.
        """
        rpm = self.state.rpm

        # Base pressure: linear with RPM between low-RPM min and normal range
        if rpm < 3500:
            # Below 3500: pressures can be lower (SOURCE: 0.8 bar min)
            frac = (rpm - self.RPM_IDLE_MIN) / (3500.0 - self.RPM_IDLE_MIN)
            base_pressure = self.OIL_PRESSURE_MIN_LOW_RPM + frac * (
                self.OIL_PRESSURE_NORMAL_MIN - self.OIL_PRESSURE_MIN_LOW_RPM
            )
        else:
            # Above 3500: normal range
            frac = (rpm - 3500.0) / (self.RPM_MAX - 3500.0)
            base_pressure = self.OIL_PRESSURE_NORMAL_MIN + frac * (
                self.OIL_PRESSURE_NORMAL_MAX - self.OIL_PRESSURE_NORMAL_MIN
            )

        # Cold start boost (ASSUMPTION: oil viscosity effect)
        # Oil temp < 0°C → significant cold boost up to 7.0 bar
        cold_factor = max(0.0, 1.0 - (self.state.oil_temperature + 20.0) / 60.0)
        cold_factor = np.clip(cold_factor, 0.0, 1.0)
        cold_boost = cold_factor * (self.OIL_PRESSURE_MAX_COLD - base_pressure)

        pressure = base_pressure + cold_boost

        # Oil degradation fault → pressure drops (ASSUMPTION)
        if self.fault.oil_degradation > 0:
            pressure *= (1.0 - 0.4 * self.fault.oil_degradation)

        self.state.oil_pressure = max(0.0, pressure)

    def _compute_oil_temperature(self):
        """
        Oil temperature dynamics.

        SOURCE: -20°C start, 50°C pre-takeoff, 50-130°C normal operation
        (OM 2.1, p. 2-5).

        ASSUMPTION: first-order thermal model. Heat input proportional to
        RPM × throttle (power). Cooling proportional to (T_oil - T_ambient).
        """
        # First-order approach to a load-dependent equilibrium temperature.
        # This avoids the previous dimensional mismatch where a very large °C/s
        # heat term forced the state into the 130°C safety clamp almost instantly.
        power_fraction = (self.state.rpm / self.RPM_MAX) * self.state.throttle_position
        target_temp = self.state.ambient_temperature + 45.0 + 55.0 * power_fraction
        # Degraded lubrication raises the equilibrium temperature (ASSUMPTION).
        target_temp += 25.0 * self.fault.oil_degradation
        dT = (target_temp - self.state.oil_temperature) * (-np.expm1(-self.dt / self.OIL_THERMAL_TC))

        self.state.oil_temperature += dT


    def _compute_coolant_temperature(self):
        """
        Coolant temperature dynamics.

        SOURCE: -20°C start, 120°C max normal operation (OM 2.1, p. 2-5).
        Coolant flow 70 L/min @ 5800 rpm (IM 75-00-00, p. 5).

        ASSUMPTION: first-order thermal model. Cooling increases with RPM
        (pump speed). Coolant leak fault reduces cooling.
        """
        power_fraction = (self.state.rpm / self.RPM_MAX) * self.state.throttle_position
        # First-order approach to a load-dependent equilibrium temperature.
        target_temp = self.state.ambient_temperature + 50.0 + 45.0 * power_fraction
        # A leak reduces cooling effectiveness, represented as a higher equilibrium.
        target_temp += 30.0 * self.fault.coolant_leak
        flow_factor = 1.0 + 0.8 * (self.state.rpm / self.RPM_MAX)
        effective_tc = self.COOLANT_THERMAL_TC / flow_factor
        dT = (target_temp - self.state.coolant_temperature) * (-np.expm1(-self.dt / effective_tc))

        self.state.coolant_temperature += dT


    def _compute_egt(self):
        """
        Exhaust gas temperature per cylinder.

        SOURCE: 4 EGT sensors (MMH, p. 483), EGT max 950°C (OM 2.1, p. 2-5),
        EGT split formula (OM 2.1, p. 2-6).

        ASSUMPTION: EGT tracks power demand (RPM × throttle × mode), scaled
        by phase-specific nominal values. Per-cylinder variation is ASSUMED
        at 15°C RMS. Injector degradation reduces combustion efficiency → lower EGT.
        """
        phase = self._get_current_phase()
        egt_nominal = self.EGT_NOMINAL_BY_PHASE.get(phase, 500.0)

        # Power demand factor
        rpm_factor = self.state.rpm / self.RPM_MAX
        throttle_factor = self.state.throttle_position
        mode_factor = 1.15 if self.state.operating_mode == OperatingMode.POWER.value else 1.0

        # EGT scales with demand relative to phase nominal
        egt_base = egt_nominal * (0.3 + 0.7 * rpm_factor * throttle_factor * mode_factor)
        egt_base = np.clip(egt_base, 100.0, self.EGT_MAX)

        # Per-cylinder variation (ASSUMPTION — independent noise per cylinder)
        self.state.egt_1 = egt_base + self.rng.normal(0, self.EGT_PER_CYL_VAR)
        self.state.egt_2 = egt_base + self.rng.normal(0, self.EGT_PER_CYL_VAR)
        self.state.egt_3 = egt_base + self.rng.normal(0, self.EGT_PER_CYL_VAR)
        self.state.egt_4 = egt_base + self.rng.normal(0, self.EGT_PER_CYL_VAR)

        # Injector degradation → lower EGT (ASSUMPTION: reduced combustion efficiency)
        if self.fault.injector_degradation > 0:
            reduction = self.fault.injector_degradation * 60.0  # °C per unit severity
            self.state.egt_1 -= reduction
            self.state.egt_2 -= reduction
            self.state.egt_3 -= reduction
            self.state.egt_4 -= reduction

        # Measurement-only bias. Operating limits are diagnostic thresholds,
        # not saturation bounds on a sensor reading.
        for idx, attr in enumerate(('egt_1', 'egt_2', 'egt_3', 'egt_4')):
            setattr(self.state, attr, getattr(self.state, attr) + self._egt_biases[idx])

    def _compute_egt_split(self):
        """EGT split = max(EGT) - min(EGT) — SOURCE-backed formula (OM 2.1, p. 2-6)."""
        egts = [self.state.egt_1, self.state.egt_2, self.state.egt_3, self.state.egt_4]
        self.state.egt_split = max(egts) - min(egts)

    def _compute_fuel_flow(self):
        """Uncalibrated BSFC approximation coupled to shaft power, in L/h.
        ECO: 270 g/kWh; POWER: 300 g/kWh (engineering assumptions).
        These imply roughly 28-31% efficiency for gasoline, not manufacturer maps.
        """
        bsfc = self.BSFC_POWER if self.state.operating_mode == 'POWER' else self.BSFC_ECO
        enrichment = 1.0 + 0.15 * np.clip((50.0 - self.state.oil_temperature) / 70.0, 0.0, 1.0)
        self.state.expected_fuel_flow = max(
            self.FUEL_FLOW_IDLE, self.state.expected_power * bsfc / self.FUEL_DENSITY_KG_L
        ) * enrichment

    def _compute_fuel_pressure(self):
        """
        Fuel rail pressure.

        SOURCE: 2.9-3.2 bar normal, 2.5-3.5 bar excursion max 3s after
        power change (OM 2.1, p. 2-6).

        ASSUMPTION: regulated at ~3.05 bar nominal with small dynamic variation.
        Filter restriction lowers downstream rail pressure (ASSUMPTION).
        The manual's rising-pressure diagnostic refers to an upstream sensor.
        """
        # Nominal target
        target = 3.05  # bar (midpoint of 2.9-3.2)

        # Dynamic variation with RPM changes (ASSUMPTION)
        rpm_change_rate = abs(self.state.rpm - getattr(self, '_prev_rpm', self.state.rpm)) / self.dt
        self._prev_rpm = self.state.rpm
        dynamic_error = 0.02 * min(rpm_change_rate / 100.0, 1.0)  # bar per power-change event

        pressure = target + dynamic_error * np.sin(self.time / 8.0)

        # Downstream pressure loss from restriction (ASSUMPTION; not upstream filter pressure)
        if self.fault.fuel_filter_clog > 0:
            pressure -= self.fault.fuel_filter_clog * 0.8  # bar per unit (ASSUMPTION)

        self.state.fuel_pressure = max(0.0, pressure)

    def _compute_vibration(self):
        """
        Vibration RMS estimate.

        SOURCE: gearbox pitting → high-frequency vibration (MMH, p. 181).
        Mechanical vibration damping in propeller gearbox (IM 00-00-00, p. 4).

        ASSUMPTION: baseline vibration proportional to RPM. No source amplitude
        available — initial scale is ASSUMPTION until calibrated.
        """
        # RPM-correlated baseline (ASSUMPTION)
        rpm_baseline = self.VIBRATION_RMS_HEALTHY_BASE * (self.state.rpm / self.RPM_MAX)

        # Bearing wear / mechanical fault component (ASSUMPTION)
        fault_component = self.VIBRATION_FAULT_PER_SEVERITY * self.fault.bearing_wear

        # High-frequency noise (ASSUMPTION)
        hf_noise = self.rng.normal(0, 0.008)

        self.vibration_rms = rpm_baseline + fault_component + hf_noise
        self.vibration_rms = max(0.0, self.vibration_rms)

    def _compute_expected_power(self):
        """Healthy reference power with both rated RPM anchors.
        Throttle scaling, above-critical-altitude derating and hot-intake
        derating are engineering assumptions, not a calibrated propeller map.
        """
        rated = np.interp(self.state.rpm,
                          [self.RPM_IDLE_MIN, self.RPM_CONTINUOUS, self.RPM_MAX],
                          [0.0, self.POWER_CONTINUOUS, self.POWER_TAKEOFF])
        altitude_factor = min(1.0, self._altitude_to_pressure(self.state.altitude) /
                              self._altitude_to_pressure(self.ALTITUDE_CRITICAL))
        temperature_factor = min(1.0, (273.15 + self.MAT_MAX_NORMAL) /
                                 (273.15 + self.state.manifold_temperature))
        self.state.expected_power = rated * self.state.throttle_position * altitude_factor * temperature_factor

    def _compute_health_score(self) -> float:
        """
        Overall engine health score (0-100).

        Project metric — ASSUMPTION scale. Based on:
        - EGT split violations (SOURCE limits)
        - EGT max violations (SOURCE limit)
        - Oil pressure out of normal range (SOURCE limits)
        - Coolant temperature over limit (SOURCE limit)
        - Fuel pressure out of normal range (SOURCE limits)
        - Observable soft indicators (ASSUMPTION penalty weights)
        """
        score = 100.0

        # EGT split
        fuel_flow = self.state.expected_fuel_flow
        egt_limit = self.EGT_SPLIT_MAX_HIGH_FUEL if fuel_flow > 3.0 else self.EGT_SPLIT_MAX_LOW_FUEL
        if self.state.egt_split > egt_limit:
            excess = self.state.egt_split / egt_limit - 1.0
            score -= 20.0 * excess

        # EGT max
        max_egt = max(self.state.egt_1, self.state.egt_2, self.state.egt_3, self.state.egt_4)
        if max_egt > self.EGT_MAX:
            score -= 30.0 * (max_egt / self.EGT_MAX - 1.0)

        # Oil pressure
        if self.state.rpm >= 3500:
            if self.state.oil_pressure < self.OIL_PRESSURE_NORMAL_MIN:
                score -= 15.0 * (1.0 - self.state.oil_pressure / self.OIL_PRESSURE_NORMAL_MIN)
            elif self.state.oil_pressure > self.OIL_PRESSURE_NORMAL_MAX:
                score -= 10.0 * (self.state.oil_pressure / self.OIL_PRESSURE_NORMAL_MAX - 1.0)
        else:
            if self.state.oil_pressure < self.OIL_PRESSURE_MIN_LOW_RPM:
                score -= 15.0

        # Coolant temperature
        if self.state.coolant_temperature > self.COOLANT_TEMP_MAX:
            score -= 20.0 * (self.state.coolant_temperature / self.COOLANT_TEMP_MAX - 1.0)

        # Fuel pressure
        if self.state.fuel_pressure < self.FUEL_PRESSURE_NORMAL_MIN or \
           self.state.fuel_pressure > self.FUEL_PRESSURE_NORMAL_MAX:
            score -= 10.0

        # Observable-only soft indicators. Never use hidden injected-fault
        # variables here: health_score may later be consumed by ML/UI and must
        # not leak the ground-truth fault label.
        if self.state.oil_temperature > 110.0:
            score -= min(15.0, (self.state.oil_temperature - 110.0) * 0.75)
        if self.state.coolant_temperature > 105.0:
            score -= min(15.0, (self.state.coolant_temperature - 105.0) * 1.0)
        if self.vibration_rms > 0.12:
            score -= min(25.0, (self.vibration_rms - 0.12) * 60.0)
        if self.state.egt_split > 100.0:
            score -= min(15.0, (self.state.egt_split - 100.0) * 0.08)

        return max(0.0, min(100.0, score))

    def _update_lane_can_state(self):
        """Electrical statuses remain placeholders. Mechanical fault labels do
        not directly manufacture CAN or EMS failures without a causal model.
        """
        pass

    def _get_current_phase(self) -> MissionPhase:
        """Return the currently active mission phase."""
        if self._current_phase_idx < len(self.mission_profile):
            return MissionPhase(self.mission_profile[self._current_phase_idx]['phase'])
        return MissionPhase.LANDING

    # =========================================================================
    # Snapshot / CSV output
    # =========================================================================

    def _make_snapshot(self) -> Dict:
        """One row of telemetry data as a dictionary."""
        active = self._active_severities(self.time)
        types = sorted({key.split(':')[0] for key in active})
        return {
            # --- Time ---
            'time_s': round(self.time, 9),

            # --- Primary inputs ---
            'rpm': round(self.state.rpm, 2),
            'throttle_position': round(self.state.throttle_position, 4),
            'ambient_pressure_hpa': round(self.state.ambient_pressure, 2),
            'ambient_temperature_c': round(self.state.ambient_temperature + 10.0 * self.fault.sensor_drift, 2),
            'altitude_ft': round(self.state.altitude, 2),

            # --- Air path ---
            'airflow_kg_s': round(self.state.airflow, 6),
            'manifold_pressure_mbar': round(self.state.manifold_pressure, 2),
            'manifold_temperature_c': round(self.state.manifold_temperature, 2),
            'boost_pressure_mbar': round(self.state.boost_pressure, 2),

            # --- Lubrication ---
            'oil_pressure_bar': round(self.state.oil_pressure, 3),
            'oil_temperature_c': round(self.state.oil_temperature, 2),

            # --- Cooling ---
            'coolant_temperature_c': round(self.state.coolant_temperature, 2),

            # --- Exhaust ---
            'egt_1_c': round(self.state.egt_1, 2),
            'egt_2_c': round(self.state.egt_2, 2),
            'egt_3_c': round(self.state.egt_3, 2),
            'egt_4_c': round(self.state.egt_4, 2),
            'egt_split_c': round(self.state.egt_split, 2),

            # --- Fuel ---
            'fuel_pressure_bar': round(self.state.fuel_pressure, 3),

            # --- EMS / CAN / Electrical ---
            'lane_a_state': self.state.lane_a_state,
            'lane_b_state': self.state.lane_b_state,
            'display_can_a_state': self.state.display_can_a_state,
            'display_can_b_state': self.state.display_can_b_state,
            'generator_state': self.state.generator_state,

            # --- Derived ---
            'operating_mode': self.state.operating_mode,
            'expected_power_kw': round(self.state.expected_power, 2),
            'expected_fuel_flow_l_h': round(self.state.expected_fuel_flow, 3),
            'health_score': round(self.state.health_score, 2),
            'vibration_rms_g': round(self.vibration_rms, 4),

            # --- Context ---
            'mission_phase': self._get_current_phase().value,
            'fault_active': int(self.is_fault_active_at(self.time)),
            'fault_type': 'none' if not types else types[0] if len(types) == 1 else 'combined',
            'fault_severity': round(max(active.values(), default=0.0), 6),
            'active_faults': json.dumps(sorted(active)),
            'fault_severities': json.dumps(active, sort_keys=True),
        }

    # =========================================================================
    # Run
    # =========================================================================

    def run(self) -> pd.DataFrame:
        """Run a fresh simulator through its duration, including a partial last step."""
        if self.time != 0.0:
            raise ValueError("run() requires a fresh simulator; use step() to continue")
        nominal_dt = self.dt
        try:
            while self.time < self.duration - 1e-9:
                self.dt = min(nominal_dt, self.duration - self.time)
                self.step()
        finally:
            self.dt = nominal_dt
        return pd.DataFrame(self.history)

    # =========================================================================
    # Fault injection
    # =========================================================================

    def inject_faults(self, fault_list):
        """Append events: (type, severity, onset, duration[, sensor_id]).
        All severities are in [0, 1]. EGT sensor_id is explicitly 1..4;
        severity 1 gives +75 C. Repeated events retain independent windows.
        """
        supported = {'oil_degradation', 'coolant_leak', 'fuel_filter_clog',
                     'injector_degradation', 'bearing_wear', 'sensor_drift', 'egt_sensor_fault'}
        events = []
        for definition in fault_list:
            if len(definition) not in (4, 5):
                raise ValueError("fault requires type, severity, onset, duration and optional sensor_id")
            ft, sv, onset, duration = definition[:4]
            sensor = definition[4] if len(definition) == 5 else None
            if ft not in supported or not np.isfinite(sv) or not 0 <= sv <= 1:
                raise ValueError("unknown fault or severity outside [0, 1]")
            if not np.isfinite(onset) or onset < 0 or np.isnan(duration) or duration <= 0:
                raise ValueError("invalid fault onset or duration")
            if ft == 'egt_sensor_fault' and sensor not in (1, 2, 3, 4):
                raise ValueError("EGT faults require explicit sensor_id in 1..4")
            if ft != 'egt_sensor_fault' and sensor is not None:
                raise ValueError("sensor_id applies only to EGT faults")
            if sv > 0:
                events.append(dict(type=ft, severity=float(sv), onset=float(onset),
                                   duration=float(duration), sensor_id=sensor))
        self._events.extend(events)
        self.fault.active = bool(self._events)

    def inject_fault(self, fault_type: str, severity: float = 0.5,
                     onset_time: float = 0.0, duration: float = float('inf'),
                     sensor_id: int | None = None):
        self.inject_faults([(fault_type, severity, onset_time, duration, sensor_id)])

    def is_fault_active_at(self, time_s: float) -> bool:
        return bool(self._active_severities(time_s))

    def _active_severities(self, time_s):
        active = {}
        for e in self._events:
            if e['onset'] <= time_s < e['onset'] + e['duration']:
                key = e['type'] + (f":{e['sensor_id']}" if e['sensor_id'] else '')
                progress = min(1.0, (time_s - e['onset']) / 60.0)
                severity = e['severity'] * progress ** 2 * (3 - 2 * progress)
                active[key] = max(active.get(key, 0.0), severity)
        return active
