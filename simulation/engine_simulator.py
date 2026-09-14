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

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
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
    manifold_pressure: float = 60.0         # mbar (SOURCE: MAPS 1/2, OM 2.1)
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
    """Active fault injection state."""

    active: bool = False
    fault_type: str = "none"
    severity: float = 0.0                   # 0.0 - 1.0
    onset_time: float = 0.0                 # seconds from simulation start
    duration: float = float('inf')          # seconds (inf = permanent)
    fault_types: list = field(default_factory=list)  # for combined scenarios

    # Per-fault degradation parameters (accumulated by inject_faults)
    oil_degradation: float = 0.0
    coolant_leak: float = 0.0
    fuel_filter_clog: float = 0.0
    injector_degradation: float = 0.0
    bearing_wear: float = 0.0
    sensor_drift: float = 0.0
    egt_sensor_fault_id: int = -1           # -1 = none, 0-3 = which EGT sensor
    egt_sensor_bias: float = 0.0            # °C bias on faulty sensor
    fault_onsets: dict = field(default_factory=dict)  # per-fault onset times

    # Base severity values snapshot — stored so gating can ramp from 0
    # back to full without losing the intended severity.
    _base_severity: dict = field(default_factory=dict)


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
    FUEL_FLOW_MAX_POWER = 5.5              # L/h  (ASSUMPTION — full takeoff power)

    # Airflow model (ASSUMPTION — displacement estimate for 915 series)
    ESTIMATED_DISPLACEMENT_L = 1.495       # L    (ASSUMPTION — 4-cyl, ~1.5L)
    VOLUMETRIC_EFFICIENCY = 0.80           # —    (ASSUMPTION)

    # Mission profile transition smoothing (ASSUMPTION)
    PHASE_TRANSITION_TC = 5.0              # seconds (ASSUMPTION)

    # Standard atmosphere approximation for ambient pressure by altitude (ASSUMPTION)
    # Using simplified barometric formula: P = 1013.25 * (1 - 2.2557e-5 * h)^5.2558
    ALTITUDE_PRESSURE_TABLE = {
        0: 1013.0,
        1000: 1001.0,
        2000: 989.0,
        3000: 977.0,
        4000: 965.0,
        5000: 953.0,
        6000: 941.0,
        7000: 929.0,
        8000: 917.0,
        9000: 905.0,
        10000: 893.0,
        12000: 869.0,
        14000: 845.0,
        16000: 821.0,
        18000: 797.0,
        20000: 774.0,
        22000: 751.0,
        23000: 739.0,
    }

    ALTITUDE_TEMP_LAPSE = -0.0065          # °C/m (ASSUMPTION — standard lapse rate)

    # =========================================================================
    # Constructor
    # =========================================================================

    def __init__(self, dt: float = 1.0, duration: float = 3600.0):
        """
        Args:
            dt:        Time step in seconds (default 1.0 → 1 Hz telemetry)
            duration:  Total simulation duration in seconds
        """
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

        The simulator linearly interpolates between phase targets with a
        first-order lag (PHASE_TRANSITION_TC). This avoids instantaneous
        jumps that would be unphysical.
        """
        self.mission_profile = list(phases)  # shallow copy
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
        """Approximate ambient pressure at a given altitude (ASSUMPTION)."""
        # Interpolate from table
        alts = sorted(self.ALTITUDE_PRESSURE_TABLE.keys())
        if altitude_ft <= alts[0]:
            return self.ALTITUDE_PRESSURE_TABLE[alts[0]]
        if altitude_ft >= alts[-1]:
            return self.ALTITUDE_PRESSURE_TABLE[alts[-1]]
        for i in range(len(alts) - 1):
            if alts[i] <= altitude_ft <= alts[i + 1]:
                frac = (altitude_ft - alts[i]) / (alts[i + 1] - alts[i])
                return self.ALTITUDE_PRESSURE_TABLE[alts[i]] + \
                       frac * (self.ALTITUDE_PRESSURE_TABLE[alts[i + 1]] -
                               self.ALTITUDE_PRESSURE_TABLE[alts[i]])
        return 1013.0

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
        self._compute_fuel_flow()
        self._compute_fuel_pressure()
        self._compute_vibration()
        self._compute_expected_power()
        self.state.health_score = self._compute_health_score()
        self._update_lane_can_state()

        # --- Time ---
        self.time += self.dt

        # --- Record ---
        snapshot = self._make_snapshot()
        self.history.append(snapshot)
        return snapshot

    # =========================================================================
    # Fault onset gating
    # =========================================================================

    def _gate_faults_by_onset(self):
        """
        Apply per-fault onset gating so each fault activates at its own
        scheduled time, not all at once.

        For each fault parameter, we compute a 0→1 ramp starting at the
        fault's onset_time. If a fault hasn't been individually timed,
        fall back to the global fault.onset_time.

        Ramp uses a sigmoid-like smoothstep so faults don't jump abruptly:
            t < onset   → 0.0 multiplier
            onset <= t < onset + 60 : smooth ramp 0→1 over 60s
            t >= onset + 60        → 1.0 multiplier

        We multiply the stored base severity by the gate factor — never
        zero the stored value, so the effect ramps up smoothly from 0 to
        full severity rather than being permanently deleted.

        The _base_severity dict stores the intended severity for each fault
        type at injection time. The public fault.X fields are what the
        physics code reads; those get gated. The base is never modified.
        """
        if not self.fault.active:
            return

        t = self.time
        gate_period = 60.0  # seconds for fault to fully ramp in (ASSUMPTION)

        # Per-fault onset from fault_onsets dict; fall back to global onset
        onset = self.fault.onset_time
        base = self.fault._base_severity

        param_map = {
            'oil_degradation': 'oil_degradation',
            'coolant_leak': 'coolant_leak',
            'fuel_filter_clog': 'fuel_filter_clog',
            'injector_degradation': 'injector_degradation',
            'bearing_wear': 'bearing_wear',
            'sensor_drift': 'sensor_drift',
        }

        for fault_key, attr_name in param_map.items():
            param_onset = self.fault.fault_onsets.get(fault_key, onset)
            intended = base.get(fault_key, 0.0)
            if t < param_onset:
                setattr(self.fault, attr_name, 0.0)
            elif intended > 0 and t < param_onset + gate_period:
                # Smooth ramp from 0 to intended severity
                progress = (t - param_onset) / gate_period
                # Smoothstep: 3t² - 2t³  (zero slope at endpoints)
                gate = 3.0 * progress ** 2 - 2.0 * progress ** 3
                setattr(self.fault, attr_name, intended * gate)
            # else: t >= onset + gate_period → full intended severity
            # Leave current as-is (it should already equal intended)

        # EGT sensor bias gating (same pattern)
        egt_key = 'egt_sensor_fault'
        egt_onset = self.fault.fault_onsets.get(egt_key, onset)
        # Find the intended bias from injection: we stored severity, convert
        egt_intended_sev = base.get(egt_key, 0.0)
        egt_intended_bias = (egt_intended_sev - int(egt_intended_sev)) * 150.0 \
            if egt_intended_sev > 0 else 0.0
        if t < egt_onset:
            self.fault.egt_sensor_bias = 0.0
        elif egt_intended_bias != 0.0 and t < egt_onset + gate_period:
            progress = (t - egt_onset) / gate_period
            gate = 3.0 * progress ** 2 - 2.0 * progress ** 3
            self.fault.egt_sensor_bias = egt_intended_bias * gate

    def _update_mission_phase(self):
        """Advance mission phases and smooth toward targets."""
        if not self.mission_profile:
            return

        self._phase_duration_remaining -= self.dt
        if self._phase_duration_remaining <= 0:
            self._advance_phase()

        # First-order lag toward phase targets
        alpha = 1.0 - np.exp(-self.dt / self.PHASE_TRANSITION_TC)
        self.state.rpm += alpha * (self._phase_target_rpm - self.state.rpm)
        self.state.throttle_position += alpha * (
            self._phase_target_throttle - self.state.throttle_position
        )
        self.state.altitude += alpha * (
            self._phase_target_altitude - self.state.altitude
        )

        # Ambient temperature tracks sea-level temp adjusted for altitude
        target_ambient_temp = self._altitude_to_temperature(
            self._phase_target_altitude, self._phase_ambient_temp
        )
        self.state.ambient_temperature += alpha * (
            target_ambient_temp - self.state.ambient_temperature
        )

        # Ambient pressure from altitude
        target_ambient_pressure = self._altitude_to_pressure(
            self._phase_target_altitude
        )
        self.state.ambient_pressure += alpha * (
            target_ambient_pressure - self.state.ambient_pressure
        )

        # Clamp to SOURCE limits
        self.state.rpm = np.clip(self.state.rpm, self.RPM_IDLE_MIN, self.RPM_MAX)
        self.state.throttle_position = np.clip(self.state.throttle_position, 0.0, 1.0)
        self.state.altitude = np.clip(self.state.altitude, 0.0, self.ALTITUDE_MAX)
        self.state.ambient_temperature = np.clip(
            self.state.ambient_temperature, self.AMBIENT_TEMP_MIN, self.AMBIENT_TEMP_MAX
        )

    # =========================================================================
    # Physics models
    # =========================================================================

    def _compute_operating_mode(self):
        """ECO vs POWER (SOURCE: OM 5.3, ~97% throttle threshold)."""
        if self.state.throttle_position >= self.ECO_THRESHOLD or \
           self.state.lane_b_state != "ACTIVE":
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
        """
        Manifold air temperature after turbo + intercooler.

        SOURCE: MATS sensor exists (OM). Intercooler is part of air path
        (OM 7.6, pp. 7-18 to 7-20).

        ASSUMPTION: simplified thermal model.
        A turbocharged engine's intake charge is always at or above ambient
        temperature — the turbo compresses air (heating it), the intercooler
        removes ~70% of the rise. At zero boost, MATS tracks ambient with a
        small positive offset from intake-path heating.

        The old adiabatic formula (T after_turbo = T_amb * (P_ratio)^((γ-1)/γ))
        produces values BELOW ambient when P_ratio < 1 (deceleration / idle),
        which is physically wrong for a forced-induction engine. Replaced with
        a linear boost-to-temp model.

        NOTE: Exact temperature behavior is not published in the uploaded
        BRP-Rotax manuals. This is an ASSUMPTION that should be calibrated
        against real or experimentally determined data when available.
        """
        t_ambient_c = self.state.ambient_temperature
        boost = self.state.boost_pressure  # mbar above ambient

        # Temperature rise from compression, before intercooler.
        # ASSUMPTION: ~0.10°C per mbar of boost (tuned so that at full rated
        # boost ~500 mbar, pre-intercooler T rise is ~50°C above ambient).
        pre_ic_rise = boost * 0.10  # °C

        # Intercooler removes 70% (ASSUMPTION — matches OM 7.6 description)
        intercooler_eff = 0.70
        post_ic_rise = pre_ic_rise * (1.0 - intercooler_eff)

        # At zero boost, intake charge is slightly above ambient from
        # ram-air heating / intake path inefficiency (ASSUMPTION, ~2°C).
        intake_offset = 2.0  # °C (ASSUMPTION — non-zero even at zero boost)

        self.state.manifold_temperature = t_ambient_c + intake_offset + post_ic_rise

        # Clamp to source limits (MAT > 50°C → reduced power in ECO mode per OM 2.1)
        self.state.manifold_temperature = np.clip(
            self.state.manifold_temperature,
            self.AMBIENT_TEMP_MIN - 5.0,  # don't go far below ambient
            self.MAT_EXTENDED_MAX
        )

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
        density = manifold_mbar / (manifold_temp_k * 287.0)  # kg/m³  (mbar → hPa, R=287)

        # Mass flow per cylinder: density * displacement_volume * RPM/60 * VE
        # 4 cylinders
        displacement_m3 = self.ESTIMATED_DISPLACEMENT_L * 1e-3
        airflow = density * displacement_m3 * (self.state.rpm / 60.0) * \
                  self.VOLUMETRIC_EFFICIENCY * 4.0

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

        self.state.oil_pressure = np.clip(
            pressure, self.OIL_PRESSURE_MIN_LOW_RPM, self.OIL_PRESSURE_MAX_COLD
        )

    def _compute_oil_temperature(self):
        """
        Oil temperature dynamics.

        SOURCE: -20°C start, 50°C pre-takeoff, 50-130°C normal operation
        (OM 2.1, p. 2-5).

        ASSUMPTION: first-order thermal model. Heat input proportional to
        RPM × throttle (power). Cooling proportional to (T_oil - T_ambient).
        """
        # Heat generation (ASSUMPTION — proportional to mechanical work)
        power_fraction = (self.state.rpm / self.RPM_MAX) * self.state.throttle_position
        heat_input = 80.0 * power_fraction  # °C/s scale (ASSUMPTION)

        # Cooling to ambient
        cooling = (self.state.oil_temperature - self.state.ambient_temperature) / \
                  self.OIL_THERMAL_TC

        # Net rate
        dT = (heat_input - cooling) * self.dt

        # Oil degradation → runs hotter (ASSUMPTION: degraded oil, worse cooling)
        if self.fault.oil_degradation > 0:
            dT *= (1.0 + 0.4 * self.fault.oil_degradation)

        self.state.oil_temperature += dT
        self.state.oil_temperature = np.clip(
            self.state.oil_temperature,
            self.OIL_TEMP_START_MIN,
            self.OIL_TEMP_NORMAL_MAX
        )

    def _compute_coolant_temperature(self):
        """
        Coolant temperature dynamics.

        SOURCE: -20°C start, 120°C max normal operation (OM 2.1, p. 2-5).
        Coolant flow 70 L/min @ 5800 rpm (IM 75-00-00, p. 5).

        ASSUMPTION: first-order thermal model. Cooling increases with RPM
        (pump speed). Coolant leak fault reduces cooling.
        """
        power_fraction = (self.state.rpm / self.RPM_MAX) * self.state.throttle_position
        heat_input = 60.0 * power_fraction  # °C/s scale (ASSUMPTION)

        # Cooling increases with RPM (pump speed) — ASSUMPTION
        flow_factor = 1.0 + 0.8 * (self.state.rpm / self.RPM_MAX)
        effective_tc = self.COOLANT_THERMAL_TC / flow_factor
        cooling = (self.state.coolant_temperature - self.state.ambient_temperature) / \
                  effective_tc

        dT = (heat_input - cooling) * self.dt

        # Coolant leak → reduced cooling → runs hotter (ASSUMPTION)
        if self.fault.coolant_leak > 0:
            dT *= (1.0 + 0.6 * self.fault.coolant_leak)

        self.state.coolant_temperature += dT
        self.state.coolant_temperature = np.clip(
            self.state.coolant_temperature,
            self.OIL_TEMP_START_MIN,
            self.COOLANT_TEMP_MAX
        )

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
        self.state.egt_1 = egt_base + np.random.normal(0, self.EGT_PER_CYL_VAR)
        self.state.egt_2 = egt_base + np.random.normal(0, self.EGT_PER_CYL_VAR)
        self.state.egt_3 = egt_base + np.random.normal(0, self.EGT_PER_CYL_VAR)
        self.state.egt_4 = egt_base + np.random.normal(0, self.EGT_PER_CYL_VAR)

        # Injector degradation → lower EGT (ASSUMPTION: reduced combustion efficiency)
        if self.fault.injector_degradation > 0:
            reduction = self.fault.injector_degradation * 60.0  # °C per unit severity
            self.state.egt_1 = max(100.0, self.state.egt_1 - reduction)
            self.state.egt_2 = max(100.0, self.state.egt_2 - reduction)
            self.state.egt_3 = max(100.0, self.state.egt_3 - reduction)
            self.state.egt_4 = max(100.0, self.state.egt_4 - reduction)

        # Specific EGT sensor bias fault
        if self.fault.egt_sensor_fault_id >= 0:
            bias = self.fault.egt_sensor_bias
            if self.fault.egt_sensor_fault_id == 0:
                self.state.egt_1 += bias
            elif self.fault.egt_sensor_fault_id == 1:
                self.state.egt_2 += bias
            elif self.fault.egt_sensor_fault_id == 2:
                self.state.egt_3 += bias
            elif self.fault.egt_sensor_fault_id == 3:
                self.state.egt_4 += bias

        # Clamp to SOURCE max
        for attr in ('egt_1', 'egt_2', 'egt_3', 'egt_4'):
            val = getattr(self.state, attr)
            setattr(self.state, attr, np.clip(val, 50.0, self.EGT_MAX))

    def _compute_egt_split(self):
        """EGT split = max(EGT) - min(EGT) — SOURCE-backed formula (OM 2.1, p. 2-6)."""
        egts = [self.state.egt_1, self.state.egt_2, self.state.egt_3, self.state.egt_4]
        self.state.egt_split = max(egts) - min(egts)

    def _compute_fuel_flow(self):
        """
        Estimated fuel flow.

        SOURCE: Rotax Performance & Fuel Consumption Model uses RPM, throttle,
        ambient pressure, ambient temperature (OM 5.1-5.2, pp. 5-2 to 5-3).
        Fuel flow data in kg/h with 10% tolerance.

        ASSUMPTION: simplified model calibrated to reasonable L/h range.
        Actual values TBD until electronic model is obtained.
        """
        rpm_factor = (self.state.rpm - self.RPM_IDLE_MIN) / (self.RPM_MAX - self.RPM_IDLE_MIN)
        rpm_factor = np.clip(rpm_factor, 0.0, 1.0)

        # ECO mode → lower fuel flow (ASSUMPTION)
        mode_factor = 0.85 if self.state.operating_mode == OperatingMode.ECO.value else 1.0

        # Altitude correction: thinner air → less fuel needed (ASSUMPTION)
        alt_fraction = self.state.altitude / self.ALTITUDE_MAX
        alt_factor = 1.0 - 0.25 * alt_fraction
        alt_factor = max(0.5, alt_factor)

        # Cold start enrichment (ASSUMPTION — ECU enrichs when cold)
        cold_enrichment = max(0.0, (50.0 - self.state.oil_temperature) / 70.0) * 0.3

        self.state.expected_fuel_flow = (
            self.FUEL_FLOW_IDLE +
            (self.FUEL_FLOW_MAX_POWER - self.FUEL_FLOW_IDLE) *
            rpm_factor * self.state.throttle_position * mode_factor * alt_factor +
            cold_enrichment
        )
        self.state.expected_fuel_flow = max(self.FUEL_FLOW_IDLE, self.state.expected_fuel_flow)

    def _compute_fuel_pressure(self):
        """
        Fuel rail pressure.

        SOURCE: 2.9-3.2 bar normal, 2.5-3.5 bar excursion max 3s after
        power change (OM 2.1, p. 2-6).

        ASSUMPTION: regulated at ~3.05 bar nominal with small dynamic variation.
        Fuel filter clog → pressure rises (SOURCE: IM 73-00-00, p. 12).
        """
        # Nominal target
        target = 3.05  # bar (midpoint of 2.9-3.2)

        # Dynamic variation with RPM changes (ASSUMPTION)
        rpm_change_rate = abs(self.state.rpm - getattr(self, '_prev_rpm', self.state.rpm)) / self.dt
        self._prev_rpm = self.state.rpm
        dynamic_error = 0.02 * min(rpm_change_rate / 100.0, 1.0)  # bar per power-change event

        pressure = target + dynamic_error * np.sin(self.time / 8.0)

        # Fuel filter clog → pressure increases (SOURCE-backed: IM 73-00-00, p. 12)
        if self.fault.fuel_filter_clog > 0:
            pressure += self.fault.fuel_filter_clog * 0.25  # bar per unit (ASSUMPTION)

        self.state.fuel_pressure = np.clip(
            pressure,
            self.FUEL_PRESSURE_EXCURSION_MIN,
            self.FUEL_PRESSURE_EXCURSION_MAX
        )

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
        hf_noise = np.random.normal(0, 0.008)

        self.vibration_rms = rpm_baseline + fault_component + hf_noise
        self.vibration_rms = max(0.0, self.vibration_rms)

    def _compute_expected_power(self):
        """
        Expected power output.

        SOURCE: 104 kW @ 5800 rpm takeoff, 99 kW @ 5500 rpm continuous
        (OM 2.1, p. 2-2).

        ASSUMPTION: power interpolates between idle (near 0) and max power
        based on RPM and throttle.
        """
        rpm_fraction = (self.state.rpm - self.RPM_IDLE_MIN) / (self.RPM_MAX - self.RPM_IDLE_MIN)
        rpm_fraction = np.clip(rpm_fraction, 0.0, 1.0)

        if self.state.operating_mode == OperatingMode.POWER.value:
            power_ref = self.POWER_TAKEOFF
        else:
            power_ref = self.POWER_CONTINUOUS

        self.state.expected_power = power_ref * rpm_fraction * self.state.throttle_position
        self.state.expected_power = max(0.0, self.state.expected_power)

    def _compute_health_score(self) -> float:
        """
        Overall engine health score (0-100).

        Project metric — ASSUMPTION scale. Based on:
        - EGT split violations (SOURCE limits)
        - EGT max violations (SOURCE limit)
        - Oil pressure out of normal range (SOURCE limits)
        - Coolant temperature over limit (SOURCE limit)
        - Fuel pressure out of normal range (SOURCE limits)
        - Active fault degradation (ASSUMPTION penalty weights)
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

        # Fault penalties (ASSUMPTION weights)
        score -= 30.0 * self.fault.oil_degradation
        score -= 25.0 * self.fault.coolant_leak
        score -= 20.0 * self.fault.fuel_filter_clog
        score -= 25.0 * self.fault.injector_degradation
        score -= 20.0 * self.fault.bearing_wear

        return max(0.0, min(100.0, score))

    def _update_lane_can_state(self):
        """
        Lane A/B and Display CAN state.

        SOURCE: dual-lane EMS (OM 7.5.1), dual Display CAN (IM 77-00-00).
        ASSUMPTION: faults can degrade lanes/CAN with low probability.
        """
        # Severe bearing wear → possible Lane A degradation (ASSUMPTION)
        if self.fault.bearing_wear > 0.6 and np.random.random() < 0.0005:
            self.state.lane_a_state = "DEGRADED"

        # Severe fuel filter clog → possible Display CAN A failure (ASSUMPTION)
        if self.fault.fuel_filter_clog > 0.7 and np.random.random() < 0.0003:
            self.state.display_can_a_state = "FAILED"

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
        return {
            # --- Time ---
            'time_s': round(self.time, 2),

            # --- Primary inputs ---
            'rpm': round(self.state.rpm, 2),
            'throttle_position': round(self.state.throttle_position, 4),
            'ambient_pressure_hpa': round(self.state.ambient_pressure, 2),
            'ambient_temperature_c': round(self.state.ambient_temperature, 2),
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
            'fault_active': int(self.fault.active),
            'fault_type': self.fault.fault_type,
            'fault_severity': round(self.fault.severity, 3),
        }

    # =========================================================================
    # Run
    # =========================================================================

    def run(self) -> pd.DataFrame:
        """Run the full simulation and return a DataFrame."""
        self.history = []
        steps = int(self.duration / self.dt)
        for _ in range(steps):
            self.step()
        return pd.DataFrame(self.history)

    # =========================================================================
    # Fault injection
    # =========================================================================

    def inject_faults(self, fault_list):
        """
        Inject multiple faults at once (for combined scenarios).
        ACCUMULATES fault parameters rather than resetting them —
        so combined_oil_and_bearing actually has both faults active.

        Args:
            fault_list: list of (fault_type, severity, onset_time, duration) tuples
        """
        self.fault.active = True
        self.fault.fault_type = 'combined'
        self.fault.severity = max(f[1] for f in fault_list) if fault_list else 0.0
        self.fault.onset_time = min(f[2] for f in fault_list) if fault_list else 0.0
        self.fault.duration = max(f[3] for f in fault_list) if fault_list else float('inf')
        self.fault.fault_types = [f[0] for f in fault_list]

        # Store per-fault onset times for gating
        self.fault.fault_onsets = {}
        self.fault._base_severity = {}
        for ft, sv, onset, dur in fault_list:
            key = ft if ft != 'egt_sensor_fault' else 'egt_sensor_fault'
            # Same fault type can be injected multiple times — keep max severity, earliest onset
            if key not in self.fault._base_severity or sv > self.fault._base_severity[key]:
                self.fault._base_severity[key] = sv
            if key not in self.fault.fault_onsets or onset < self.fault.fault_onsets[key]:
                self.fault.fault_onsets[key] = onset

        # Do NOT reset — accumulate each fault parameter (max severity wins for same type)
        for fault_type, severity, onset, dur in fault_list:
            if fault_type == 'oil_degradation':
                self.fault.oil_degradation = max(self.fault.oil_degradation, severity)
            elif fault_type == 'coolant_leak':
                self.fault.coolant_leak = max(self.fault.coolant_leak, severity)
            elif fault_type == 'fuel_filter_clog':
                self.fault.fuel_filter_clog = max(self.fault.fuel_filter_clog, severity)
            elif fault_type == 'injector_degradation':
                self.fault.injector_degradation = max(self.fault.injector_degradation, severity)
            elif fault_type == 'bearing_wear':
                self.fault.bearing_wear = max(self.fault.bearing_wear, severity)
            elif fault_type == 'sensor_drift':
                self.fault.sensor_drift = max(self.fault.sensor_drift, severity)
            elif fault_type == 'egt_sensor_fault':
                sensor_id = int(severity) % 4
                bias = (severity - sensor_id) * 150.0
                if self.fault.egt_sensor_fault_id == -1 or abs(bias) > abs(self.fault.egt_sensor_bias):
                    self.fault.egt_sensor_fault_id = sensor_id
                    self.fault.egt_sensor_bias = bias

    def inject_fault(self, fault_type: str, severity: float = 0.5,
                     onset_time: float = 0.0, duration: float = float('inf')):
        """
        Inject a single fault. Delegates to inject_faults for consistency.
        """
        self.inject_faults([(fault_type, severity, onset_time, duration)])

    def is_fault_active_at(self, time_s: float) -> bool:
        """Check if fault is active at a given time."""
        if not self.fault.active:
            return False
        if time_s < self.fault.onset_time:
            return False
        if self.fault.duration < float('inf') and time_s > self.fault.onset_time + self.fault.duration:
            return False
        return True
