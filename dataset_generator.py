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
from datetime import datetime, timezone

from simulation.engine_simulator import (
    Rotax915Simulator,
    MissionPhase,
    OperatingMode,
)

# ============================================================================
# Output paths
# ============================================================================

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
CSV_PATH = os.path.join(OUTPUT_DIR, 'dataset.csv')
META_PATH = os.path.join(OUTPUT_DIR, 'dataset_meta.json')

os.makedirs(OUTPUT_DIR, exist_ok=True)

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
            'ambient_temp': 25.0 - 0.0065 * 12000 * 0.3048,  # lapse rate (ASSUMPTION)
            'description': 'Climb to cruise altitude — continuous power 99 kW@5500 (SOURCE)',
        },
        {
            'phase': MissionPhase.CRUISE.value,
            'duration': 900,                 # 15 min cruise / patrol
            'target_rpm': 4800,              # (ASSUMPTION — ECO mode typical cruise)
            'target_throttle': 0.70,
            'target_altitude': 12000,
            'ambient_temp': 25.0 - 0.0065 * 12000 * 0.3048,
            'description': 'Cruise / patrol — ECO mode (ASSUMPTION)',
        },
        {
            'phase': MissionPhase.HIGH_LOAD.value,
            'duration': 120,                 # 2 min high power (combat / emergency)
            'target_rpm': 5500,
            'target_throttle': 0.97,
            'target_altitude': 12000,
            'ambient_temp': 25.0 - 0.0065 * 12000 * 0.3048,
            'description': 'High load — near max continuous, POWER mode (ASSUMPTION)',
        },
        {
            'phase': MissionPhase.CRUISE.value,
            'duration': 600,                 # 10 min resume patrol
            'target_rpm': 4800,
            'target_throttle': 0.65,
            'target_altitude': 12000,
            'ambient_temp': 25.0 - 0.0065 * 12000 * 0.3048,
            'description': 'Resume cruise — ECO mode (ASSUMPTION)',
        },
        {
            'phase': MissionPhase.CLIMB.value,
            'duration': 90,                  # 1.5 min climb to loiter altitude
            'target_rpm': 5500,
            'target_throttle': 0.90,
            'target_altitude': 15000,        # critical altitude (SOURCE: OM 2.1, p. 2-2)
            'ambient_temp': 25.0 - 0.0065 * 15000 * 0.3048,
            'description': 'Climb to loiter altitude — near critical altitude (SOURCE)',
        },
        {
            'phase': MissionPhase.CRUISE.value,
            'duration': 600,                 # 10 min loiter
            'target_rpm': 4500,
            'target_throttle': 0.60,
            'target_altitude': 15000,
            'ambient_temp': 25.0 - 0.0065 * 15000 * 0.3048,
            'description': 'Loiter at critical altitude — ECO mode (SOURCE+ASSUMPTION)',
        },
        {
            'phase': MissionPhase.DESCENT.value,
            'duration': 180,                 # 3 min descent
            'target_rpm': 4000,
            'target_throttle': 0.40,
            'target_altitude': 5000,
            'ambient_temp': 25.0 - 0.0065 * 5000 * 0.3048,
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
# fault_def = (fault_type, severity, onset_time, duration)

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
        'Fuel filter gradually clogs. Per SOURCE (IM 73-00-00, p. 12): increased '
        'pressure beyond limit indicates contaminated fine filter. Fuel pressure '
        'rises, eventually affecting fuel delivery.',
        [
            ('fuel_filter_clog', 0.7, 2400, float('inf')),
        ],
    ),
    (
        'injector_degradation',
        'One or more fuel injectors degrade / partially block. ASSUMPTION — exact '
        'signatures not yet source-characterized. Reduces combustion efficiency → '
        'lower EGT, higher fuel consumption, roughness.',
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
            ('egt_sensor_fault', 1.0, 1200, float('inf')),  # severity encodes sensor id=1
        ],
    ),
    (
        'egt_sensor_3_bias',
        'EGT sensor 3 bias — tests per-cylinder fault detection vs. aggregate.',
        [
            ('egt_sensor_fault', 3.0, 800, float('inf')),
        ],
    ),
    (
        'egt_sensor_split_fault',
        'EGT sensor 2 and 4 both biased in opposite directions — inflates EGT_split, '
        'which has SOURCE-backed diagnostic value (OM 2.1, p. 2-6).',
        [
            ('egt_sensor_fault', 2.0, 1500, float('inf')),
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

def run_all_scenarios(
    dt: float = 1.0,
    duration_hours: float = 3.5,  # enough for all scenarios including late onsets
):
    """
    Run all fault scenarios and produce a combined dataset.

    Args:
        dt:             Time step in seconds (1.0 = 1 Hz)
        duration_hours: Total simulation time per scenario

    Returns:
        DataFrame with all telemetry rows, plus metadata dict.
    """
    duration = int(duration_hours * 3600)
    mission = build_mission_profile()
    rows = []
    meta = {
        'generated_at': datetime.now(tz=None).isoformat(),
        'simulator': 'Rotax915Simulator (MVP v1)',
        'engine_model': 'ROTAX 915 i A / C24 (see engine-baseline.md)',
        'variant_note': (
            'The SIH problem statement references ROTAX 915 iS series. '
            'This simulator implements the 915 i A/C24 baseline from '
            'docs/engine-baseline.md. Differences vs 915 iS are TBD until '
            'the correct manual set is obtained. Do not treat ASSUMPTION '
            'values as manufacturer specifications for the iS variant.'
        ),
        'mission_profile': mission,
        'scenarios': [],
        'evidence_policy': (
            'SOURCE = directly from BRP-Rotax manuals (OM, IM, MMH). '
            'DERIVED = calculated from source-backed values. '
            'ASSUMPTION = engineering judgement where manuals are silent. '
            'TBD = not yet defined. '
            'See engine-baseline.md sections 0 and 20 for full policy.'
        ),
        'columns': [],
        'row_count': 0,
        'fault_event_count': 0,
    }

    for scenario_name, scenario_desc, fault_defs in SCENARIOS:
        sim = Rotax915Simulator(dt=dt, duration=duration)
        sim.set_mission_profile(mission)

        # Inject faults — use inject_faults for combined scenarios,
        # inject_fault for single-fault scenarios, skip if empty
        if len(fault_defs) > 1:
            sim.inject_faults([(ft, sv, on, du) for ft, sv, on, du in fault_defs])
        elif len(fault_defs) == 1:
            ft, sv, on, du = fault_defs[0]
            sim.inject_fault(ft, severity=sv, onset_time=on, duration=du)
        # else: empty list — healthy baseline, no faults injected

        meta['fault_event_count'] += len(fault_defs)

        # Run
        df = sim.run()

        # Add scenario labels
        df['scenario_name'] = scenario_name
        df['scenario_description'] = scenario_desc
        df['has_fault'] = int(len(fault_defs) > 0)

        # Record meta for this scenario
        tmin = float(df['time_s'].min())
        tmax = float(df['time_s'].max())
        meta['scenarios'].append({
            'name': scenario_name,
            'description': scenario_desc,
            'fault_count': len(fault_defs),
            'row_count': len(df),
            'time_range_s': [tmin, tmax],
        })

        rows.append(df)

        print(f"  [OK] {scenario_name:40s}  {len(df):6d} rows  "
              f"fault={'yes' if len(fault_defs) > 0 else 'no'}"
              f"  t=[{df['time_s'].min():.0f}, {df['time_s'].max():.0f}]s")

    # Concatenate
    combined = pd.concat(rows, ignore_index=True)

    # Round numeric columns for cleaner CSV
    numeric_cols = combined.select_dtypes(include='number').columns
    for col in numeric_cols:
        combined[col] = combined[col].round(6)

    # Store column order meta
    meta['columns'] = [str(c) for c in combined.columns]
    meta['row_count'] = len(combined)
    meta['duration_hours'] = duration / 3600.0
    meta['time_step_s'] = dt

    print(f"\n  Total: {len(combined):,} rows across {len(SCENARIOS)} scenarios")
    print(f"  Output: {CSV_PATH}")

    return combined, meta


def main():
    print("=" * 70)
    print("  SIH26054 — Dataset Generator")
    print("  ROTAX 915 Digital Twin — Physics-Based Telemetry")
    print("=" * 70)
    print(f"\n  Time step: 1.0 s   Duration: 3.5 h per scenario")
    print(f"  Mission phases: 10   Scenarios: {len(SCENARIOS)}")
    print()

    combined, meta = run_all_scenarios(dt=1.0, duration_hours=3.5)

    # Write CSV
    combined.to_csv(CSV_PATH, index=False)

    # Write metadata
    with open(META_PATH, 'w') as f:
        json.dump(meta, f, indent=2, default=str)

    print(f"  Metadata: {META_PATH}")
    print()
    print("=" * 70)
    print("  Generated dataset.csv — ready for ML layer")
    print(f"  Rows: {meta['row_count']:,}")
    print(f"  Columns: {len(meta['columns'])}")
    print(f"  Scenarios: {len(meta['scenarios'])}")
    print(f"  Fault events: {meta['fault_event_count']}")
    print("=" * 70)

    # Quick summary of columns
    print("\n  Column summary:")
    signal_cols = [c for c in meta['columns'] if not c.startswith('scenario') and c not in ('has_fault',)]
    for c in signal_cols:
        print(f"    - {c}")

    print("\n  Scenario breakdown:")
    for s in meta['scenarios']:
        print(f"    {s['name']:40s}  {s['row_count']:6d} rows")

    return combined


if __name__ == '__main__':
    main()
