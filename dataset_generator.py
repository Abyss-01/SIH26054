# dataset_generator.py
#
# Generates dataset.csv from the ROTAX 915 simulator for the ML layer.
#
# This script:
#   1. Defines mission profiles (healthy baseline + various fault scenarios)
#   2. Runs the engine simulator for each scenario
#   3. Outputs dataset.csv with labeled scenarios for supervised ML

import numpy as np
import pandas as pd
import os
import json
import hashlib
from pathlib import Path
import simulation.engine_simulator as simulator_module
from datetime import datetime, timezone

from simulation.engine_simulator import (
    Rotax915Simulator,
    MissionPhase,
    OperatingMode,
)

# ============================================================================
# Output paths
# ============================================================================

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'data')
CSV_PATH = os.path.join(OUTPUT_DIR, 'dataset.csv')
META_PATH = os.path.join(OUTPUT_DIR, 'dataset_meta.json')


# ============================================================================
# Mission profile builder
# ============================================================================

def build_mission_profile():
    """
    Build a representative MALE-UAV mission profile.

    All time/duration/altitude/RPM/throttle values are ASSUMPTION —
    the Rotax manuals do not publish a MALE-UAV mission profile.
    These values are within SOURCE-backed operating limits only.

    Mission phases:
        start       → warm-up on ground
        takeoff     → max power climb to altitude
        climb       → continuing ascent
        cruise      → loiter / patrol at altitude
        high_load   → sustained high-power segment (e.g. combat / diversion)
        descent     → power reduction, descending
        landing     → final approach, landing, cooldown
    """
    return [
        {
            'phase': MissionPhase.START.value,
            'duration': 120,                 # 2 min warm-up on ground
            'target_rpm': 1800,              # idle (SOURCE: OM 2.1, p. 2-2)
            'target_throttle': 0.05,
            'target_altitude': 0,
            'ambient_temp': 25.0,
            'description': 'Ground start / warm-up',
        },
        {
            'phase': MissionPhase.TAKEOFF.value,
            'duration': 60,                  # 1 min takeoff roll + initial climb
            'target_rpm': 5800,              # max takeoff RPM (SOURCE: OM 2.1, p. 2-2)
            'target_throttle': 1.0,
            'target_altitude': 800,
            'ambient_temp': 25.0,
            'description': 'Takeoff — max power, 104 kW @ 5800 rpm (SOURCE)',
        },
        {
            'phase': MissionPhase.CLIMB.value,
            'duration': 180,                 # 3 min climb to cruise altitude
            'target_rpm': 5500,              # continuous power RPM (SOURCE: OM 2.1, p. 2-2)
            'target_throttle': 0.95,
            'target_altitude': 12000,
            'ambient_temp': 25.0,  # lapse rate (ASSUMPTION)
            'description': 'Climb to cruise altitude — continuous power 99 kW@5500 (SOURCE)',
        },
        {
            'phase': MissionPhase.CRUISE.value,
            'duration': 900,                 # 15 min cruise / patrol
            'target_rpm': 4800,              # (ASSUMPTION — ECO mode typical cruise)
            'target_throttle': 0.70,
            'target_altitude': 12000,
            'ambient_temp': 25.0,
            'description': 'Cruise / patrol — ECO mode (ASSUMPTION)',
        },
        {
            'phase': MissionPhase.HIGH_LOAD.value,
            'duration': 120,                 # 2 min high power (combat / emergency)
            'target_rpm': 5500,
            'target_throttle': 0.98,
            'target_altitude': 12000,
            'ambient_temp': 25.0,
            'description': 'High load — near max continuous, POWER mode (ASSUMPTION)',
        },
        {
            'phase': MissionPhase.CRUISE.value,
            'duration': 600,                 # 10 min resume patrol
            'target_rpm': 4800,
            'target_throttle': 0.65,
            'target_altitude': 12000,
            'ambient_temp': 25.0,
            'description': 'Resume cruise — ECO mode (ASSUMPTION)',
        },
        {
            'phase': MissionPhase.CLIMB.value,
            'duration': 90,                  # 1.5 min climb to loiter altitude
            'target_rpm': 5500,
            'target_throttle': 0.90,
            'target_altitude': 15000,        # critical altitude (SOURCE: OM 2.1, p. 2-2)
            'ambient_temp': 25.0,
            'description': 'Climb to loiter altitude — near critical altitude (SOURCE)',
        },
        {
            'phase': MissionPhase.CRUISE.value,
            'duration': 600,                 # 10 min loiter
            'target_rpm': 4500,
            'target_throttle': 0.60,
            'target_altitude': 15000,
            'ambient_temp': 25.0,
            'description': 'Loiter at critical altitude — ECO mode (SOURCE+ASSUMPTION)',
        },
        {
            'phase': MissionPhase.DESCENT.value,
            'duration': 180,                 # 3 min descent
            'target_rpm': 4000,
            'target_throttle': 0.40,
            'target_altitude': 5000,
            'ambient_temp': 25.0,
            'description': 'Descent — power reduction (ASSUMPTION)',
        },
        {
            'phase': MissionPhase.LANDING.value,
            'duration': 120,                 # 2 min landing + cooldown
            'target_rpm': 1800,
            'target_throttle': 0.05,
            'target_altitude': 0,
            'ambient_temp': 25.0,
            'description': 'Landing / cooldown — idle, at least 2 min cooling (SOURCE: OM 2.1)',
        },
    ]


# ============================================================================
# Fault scenario definitions
# ============================================================================

# Each scenario: (name, description, [(fault_def), ...])
# fault_def = (fault_type, normalized severity, onset_time, duration[, EGT sensor_id])

SCENARIOS = [
    # ------------------------------------------------------------------
    # Healthy baseline — no faults
    # ------------------------------------------------------------------
    (
        'healthy_baseline',
        'No faults injected. Full mission profile with SOURCE-backed limits.',
        [],
    ),

    # ------------------------------------------------------------------
    # Gradual degradation scenarios (good for RUL / degradation tracking)
    # ------------------------------------------------------------------
    (
        'oil_degradation_gradual',
        'Oil degradation progresses from onset_time. Simulates wear of oil pump / '
        ' lubrication system over time.',
        [
            ('oil_degradation', 0.6, 3600, float('inf')),  # starts after ~1h (extended)
        ],
    ),
    (
        'coolant_leak_progressive',
        'Coolant leak develops slowly. Simulates pinhole leak / heat exchanger '
        'degradation. Engine runs hotter over time.',
        [
            ('coolant_leak', 0.5, 1800, float('inf')),
        ],
    ),
    (
        'fuel_filter_clog',
        'Fuel filter restriction lowers downstream fuel rail pressure (ASSUMPTION). '
        'The manual rising-pressure diagnostic refers to a sensor upstream of the filter.',
        [
            ('fuel_filter_clog', 0.7, 2400, float('inf')),
        ],
    ),
    (
        'injector_degradation',
        'One or more fuel injectors degrade / partially block. ASSUMPTION — exact '
        'signatures not yet source-characterized. Reduces combustion efficiency → '
        'lower EGT. Fuel and power outputs remain healthy reference estimates.',
        [
            ('injector_degradation', 0.5, 3000, float('inf')),
        ],
    ),
    (
        'bearing_wear_onset',
        'Bearing wear begins. Per SOURCE (MMH, p. 181): gearbox pitting can cause '
        'high-frequency vibrations detectable by dynamic engine analysis. '
        'ASSUMPTION: vibration rises with wear severity.',
        [
            ('bearing_wear', 0.6, 4200, float('inf')),
        ],
    ),

    # ------------------------------------------------------------------
    # Sensor fault scenarios (important for anomaly detection robustness)
    # ------------------------------------------------------------------
    (
        'egt_sensor_1_bias',
        'EGT sensor 1 develops a positive bias. Simulates sensor drift / calibration '
        'error. ASSUMPTION: bias magnitude. Tests whether ML can detect sensor faults '
        'vs. real engine faults.',
        [
            ('egt_sensor_fault', 1.0, 1200, float('inf'), 1),
        ],
    ),
    (
        'egt_sensor_3_bias',
        'EGT sensor 3 bias — tests per-cylinder fault detection vs. aggregate.',
        [
            ('egt_sensor_fault', 1.0, 800, float('inf'), 3),
        ],
    ),
    (
        'egt_sensor_2_bias',
        'EGT sensor 2 develops a positive bias, increasing per-cylinder EGT disagreement '
        'and therefore EGT_split.',
        [
            ('egt_sensor_fault', 1.0, 1500, float('inf'), 2),
        ],
    ),
    (
        'sensor_drift_ambient',
        'Ambient temperature sensor drifts upward over time. ASSUMPTION — tests '
        'whether ML/ML can detect sensor drift vs. real thermal events.',
        [
            ('sensor_drift', 0.4, 2000, float('inf')),
        ],
    ),

    # ------------------------------------------------------------------
    # Multi-fault combined scenario (realistic: engines rarely have one fault)
    # ------------------------------------------------------------------
    (
        'combined_oil_and_bearing',
        'Oil degradation + bearing wear. Simulates progressive mechanical system '
        'degradation. Two faults onset at different times — tests temporal '
        'fault attribution.',
        [
            ('oil_degradation', 0.4, 1800, float('inf')),
            ('bearing_wear', 0.5, 3600, float('inf')),
        ],
    ),
    (
        'combined_coolant_and_injector',
        'Coolant leak + injector degradation. Thermal + combustion combined fault. '
        'Tests whether ML can disentangle coupled symptoms.',
        [
            ('coolant_leak', 0.4, 1200, float('inf')),
            ('injector_degradation', 0.3, 2400, float('inf')),
        ],
    ),
]

# ============================================================================
# Run all scenarios and build dataset
# ============================================================================

# Inputs available to a consumer; labels and scenario identity must never enter X.
# Health is an observable-derived indicator, omitted to avoid circular health targets.
FEATURE_COLUMNS = [
    'rpm', 'throttle_position', 'ambient_pressure_hpa', 'ambient_temperature_c',
    'altitude_ft', 'airflow_kg_s', 'manifold_pressure_mbar', 'manifold_temperature_c',
    'boost_pressure_mbar', 'oil_pressure_bar', 'oil_temperature_c',
    'coolant_temperature_c', 'egt_1_c', 'egt_2_c', 'egt_3_c', 'egt_4_c',
    'egt_split_c', 'fuel_pressure_bar', 'operating_mode', 'expected_power_kw',
    'expected_fuel_flow_l_h', 'vibration_rms_g',
]
LABEL_COLUMNS = ['fault_active', 'fault_type', 'fault_severity', 'active_faults', 'fault_severities']


def prepare_mission(duration, rng, vary=True):
    """Extend existing cruise segments to fill the requested duration.
    Small run-to-run operating variations are engineering assumptions.
    """
    mission = build_mission_profile()
    minimum = sum(p['duration'] for p in mission)
    if duration < minimum:
        raise ValueError(f"duration must be at least {minimum} seconds to complete the mission")
    cruise = [p for p in mission if p['phase'] == 'cruise']
    cruise_duration = sum(p['duration'] for p in cruise)
    for p in cruise:
        p['duration'] += (duration - minimum) * p['duration'] / cruise_duration
        if vary:
            p['target_rpm'] += float(rng.uniform(-100, 100))
            p['target_throttle'] += float(rng.uniform(-0.02, 0.02))
    sea_level_temp = float(rng.uniform(20.0, 30.0)) if vary else 25.0
    for p in mission:
        p['ambient_temp'] = sea_level_temp
    return mission


def validate_run(df, events, duration):
    """Reject malformed telemetry or labels before exporting a run."""
    if df.empty or df.isna().any().any():
        raise ValueError("empty run or missing values")
    if not np.isfinite(df.select_dtypes(include='number').to_numpy()).all():
        raise ValueError("non-finite telemetry")
    if not df.time_s.is_monotonic_increasing or df.time_s.duplicated().any():
        raise ValueError("timestamps must strictly increase within a run")
    if not np.isclose(df.time_s.iloc[-1], duration):
        raise ValueError("run does not reach requested duration")
    active = np.zeros(len(df), dtype=bool)
    for event in events:
        active |= (df.time_s >= event['onset']) & (df.time_s < event['onset'] + event['duration'])
    if not np.array_equal(df.fault_active.to_numpy(), active.astype(int)):
        raise ValueError("fault activity disagrees with event schedule")
    if not df.loc[~active, 'fault_type'].eq('none').all():
        raise ValueError("inactive samples carry a fault type")
    if len({e['type'] for e in events}) == 1 and df.loc[active, 'fault_type'].eq('combined').any():
        raise ValueError("single fault type incorrectly labelled combined")
    if not df.fault_severity.between(0, 1).all():
        raise ValueError("severity must be normalized")
    egts = df[[f'egt_{i}_c' for i in range(1, 5)]]
    if not np.allclose(egts.max(axis=1) - egts.min(axis=1), df.egt_split_c, atol=0.011):
        raise ValueError("EGT split disagrees with sensor channels")


def run_all_scenarios(dt=1.0, duration_hours=3.5, seed=42, runs_per_scenario=3):
    """Return telemetry and provenance. Group evaluation by run_id: a run_id
    shares one mission across all scenarios and must stay in one data split.
    Three runs allow a basic grouped split; they do not establish real-world validity.
    """
    duration = float(duration_hours) * 3600.0
    if not np.isfinite(dt) or dt <= 0 or not np.isfinite(duration) or duration <= 0:
        raise ValueError("dt and duration must be finite and positive")
    if not isinstance(runs_per_scenario, int) or runs_per_scenario < 1:
        raise ValueError("runs_per_scenario must be a positive integer")
    seed_sequence = np.random.SeedSequence(seed)
    rows = []
    meta = {
        'schema_version': 2,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'simulator': 'Rotax915Simulator reviewed synthetic model v2',
        'engine_model': 'ROTAX 915 i A / C24 reference',
        'evidence_policy': 'Rated limits are reference values; dynamics, BSFC, fault amplitudes and mission variations remain uncalibrated engineering assumptions.',
        'source_sha256': {
            'simulator': hashlib.sha256(Path(simulator_module.__file__).read_bytes()).hexdigest(),
            'generator': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        'numpy_version': np.__version__, 'pandas_version': pd.__version__,
        'seed': seed, 'duration_hours': duration_hours, 'time_step_s': dt,
        'runs_per_scenario': runs_per_scenario,
        'feature_columns': FEATURE_COLUMNS, 'label_columns': LABEL_COLUMNS,
        'split_group_column': 'run_id',
        'label_semantics': {
            'fault_active': 'Any scheduled positive-severity event in [onset, end); severity is zero exactly at onset.',
            'fault_severity': 'Maximum effective normalized severity after the 60-second ramp.',
            'active_faults': 'JSON list of active types; EGT identities include :sensor_id (1..4).',
            'fault_severities': 'JSON mapping from active identity to effective severity.',
            'has_fault': 'Scenario contains a fault event; NOT a current-fault target.',
            'health_score': 'Limited observable-condition indicator, not complete fault ground truth.',
        },
        'scenarios': [], 'fault_event_count': 0,
    }
    for run_index, child_seed in enumerate(seed_sequence.spawn(runs_per_scenario)):
        run_seed = int(child_seed.generate_state(1)[0])
        rng = np.random.default_rng(run_seed)
        mission = prepare_mission(duration, rng, vary=runs_per_scenario > 1)
        flight_end = duration - mission[-1]['duration']
        for scenario_name, scenario_desc, definitions in SCENARIOS:
            simulation_seed = int(rng.integers(0, 2**32))
            events = []
            for definition in definitions:
                ft, severity, onset, event_duration = definition[:4]
                if runs_per_scenario > 1:
                    onset *= float(rng.uniform(0.85, 1.15))
                if onset + 60 >= flight_end:
                    raise ValueError(f"{scenario_name}: fault must ramp in before landing; increase duration")
                events.append((ft, severity, onset, event_duration, *definition[4:]))
            sim = Rotax915Simulator(dt=dt, duration=duration, seed=simulation_seed)
            sim.set_mission_profile(mission)
            sim.inject_faults(events)
            df = sim.run()
            validate_run(df, sim._events, duration)
            df['scenario_name'] = scenario_name
            df['scenario_description'] = scenario_desc
            df['has_fault'] = int(bool(events))
            df['run_id'] = f'run_{run_index:03d}'
            df['simulation_seed'] = simulation_seed
            rows.append(df)
            meta['fault_event_count'] += len(events)
            meta['scenarios'].append({
                'name': scenario_name, 'description': scenario_desc,
                'run_id': f'run_{run_index:03d}', 'run_seed': run_seed,
                'simulation_seed': simulation_seed, 'mission_profile': mission,
                'events': [{**e, 'duration': None if np.isinf(e['duration']) else e['duration']}
                           for e in sim._events],
                'fault_count': len(events), 'row_count': len(df),
                'time_range_s': [float(df.time_s.iloc[0]), float(df.time_s.iloc[-1])],
            })
            print(f"[OK] run={run_index} {scenario_name}: {len(df)} rows", flush=True)
    combined = pd.concat(rows, ignore_index=True)
    meta['columns'] = list(combined.columns)
    meta['row_count'] = len(combined)
    meta['scenario_count'] = len(SCENARIOS)
    meta['non_feature_columns'] = [c for c in combined.columns if c not in FEATURE_COLUMNS]
    return combined, meta


def main():
    combined, meta = run_all_scenarios()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    combined.to_csv(CSV_PATH, index=False)
    with open(META_PATH, 'w') as f:
        json.dump(meta, f, indent=2, allow_nan=False)
    print(f"Wrote {len(combined):,} rows to {CSV_PATH}")
    print(f"Metadata: {META_PATH}")
    return combined


if __name__ == '__main__':
    main()
