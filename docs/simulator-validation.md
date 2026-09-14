# Simulator and dataset generation

Run from the repository root:

```bash
python -m unittest discover -s tests -v
python dataset_generator.py
```

The generator writes `data/dataset.csv` and `data/dataset_meta.json`. Imports no
longer create directories. Generated outputs are ignored by Git. The default is
12 scenarios, three independent seeded runs per scenario, 3.5 hours per run,
sampled at 1 Hz: 453,600 rows. `run_all_scenarios()` also accepts `seed`,
`runs_per_scenario`, `dt`, and `duration_hours` and returns data without writing it.

## Corrections

- Airflow uses pressure in Pa and total displacement with RPM/120 for a
  four-stroke engine. Total displacement is 1.352 L.
- Atmospheric pressure uses the tropospheric formula with altitude converted
  from feet to metres. Intake compression heating uses absolute pressure ratio.
- Power interpolation meets the 99 kW/5500 RPM and 104 kW/5800 RPM anchors at
  full throttle, below critical altitude with normal intake temperature.
- Fuel consumption uses assumed brake-specific fuel consumption of 270 g/kWh
  in ECO and 300 g/kWh in POWER, gasoline density 0.745 kg/L, and an idle floor.
  These replace the energy-inconsistent 5.5 L/h maximum; they are not Rotax maps.
- Thermal states approach load-dependent equilibria using an exponential update.
  Operating limits no longer clamp oil/coolant temperatures, oil/fuel pressures,
  or EGT sensor readings at their alarm thresholds.
- Each fault event retains its onset, duration, severity and optional sensor ID.
  Events ramp over 60 seconds and expire independently. Repeated events of the
  same type use the largest effective severity while their windows overlap.
- Ambient drift adds up to 10 C times severity to the reported measurement;
  it does not heat the physical environment or other engine states.
- EGT faults require an explicit sensor ID, 1 through 4, and normalized severity.
  Severity 1 means +75 C bias. Multiple channels can have independent events.
- Fuel filter restriction lowers the downstream rail-pressure proxy. Rising
  pressure before the filter is a different measurement location.
- Altitude reaches each phase endpoint over that phase's duration. Extra
  mission time extends cruise segments, rather than holding landing for hours.
  High-load throttle is 0.98 so the lagged command crosses the POWER threshold.
- Health uses observable conditions. Mechanical fault labels no longer directly
  cause arbitrary CAN/EMS failures; electrical columns remain placeholders.

## Labels and reproducibility

`time_s` denotes the sample at the end of a step. An event is active in the
half-open interval `[onset, onset + duration)`. Its effective severity is zero
exactly at onset, increases smoothly over 60 seconds, then reaches its requested
value. Expiry removes the forcing; thermal recovery can continue afterward.

`fault_type` is `none`, a single active fault type, or `combined` when multiple
types are active. `fault_severity` is the largest effective normalized severity.
`active_faults` and `fault_severities` are JSON strings recording individual
identities and effective severities. EGT identities include the channel, for
example `egt_sensor_fault:3`.

`has_fault` remains a **scenario annotation**, not a per-sample target. A scenario
can have a scheduled future fault while its current `fault_active` is zero.
`health_score` is a limited condition indicator, not a fault/no-fault label.

Use the metadata's explicit `feature_columns` list for predictors. Never include
fault labels, scenario descriptions, seeds, or run identity in predictors. If
constructing preprocessing or derived features, fit learned transformations
using training data only. Expected power and fuel flow are model estimates,
not independent physical sensors.

Split by **`run_id`**, keeping every scenario sharing a run ID in the same split.
These scenarios share a mission, so splitting by `(scenario_name, run_id)` alone
would still allow the same operating schedule into multiple splits. Build time
windows separately within each `(run_id, scenario_name)` trajectory.

Each run varies cruise RPM by +/-100 RPM, cruise throttle by +/-0.02, sea-level
temperature within 20–30 C, and fault onset by +/-15%. These perturbations are
engineering assumptions. One-run generation disables mission/onset variation
for controlled comparisons. Seeds, exact missions, event definitions, source
SHA-256 hashes and NumPy/pandas versions are recorded in metadata. An event
duration of JSON `null` means permanent.

## Validation and limitations

Regression tests cover dimensional airflow, rated power and fuel-energy
plausibility, atmosphere, ramp completion at multiple timesteps, expiry and
overlapping events, sensor channels and measurement-only drift, unclipped
thermal faults, mission coverage, partial final steps, and seeded reproducibility.
Each generated run is checked for finite values, increasing timestamps, schedule
agreement, normalized labels, and EGT split consistency before export.

This remains an uncalibrated synthetic model. Thermal constants, volumetric
efficiency, compressor/intercooler efficiencies, BSFC, fault signatures and
mission variations require experimental validation. It has no aircraft/propeller
dynamic model or validated remaining-useful-life model. Three run groups enable
a basic grouped evaluation, but do not establish generalization to real engines.
Do not transfer old models trained on the previous feature scales without
retraining. The previous EGT API that encoded channel number as severity is
intentionally rejected; use `sensor_id` explicitly.

References: [project engine baseline](engine-baseline.md),
[Rotax 915 specifications](https://www.flyrotax.com/products/915-is-a-isc-a),
[NASA ideal gas relationship](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/equation-of-state/),
and [DOE gasoline energy content](https://afdc.energy.gov/fuels/properties).
