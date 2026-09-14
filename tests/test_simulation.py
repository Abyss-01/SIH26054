import contextlib
import io
import json
import unittest

import numpy as np
import pandas as pd

from dataset_generator import FEATURE_COLUMNS, SCENARIOS, prepare_mission, run_all_scenarios
from simulation.engine_simulator import Rotax915Simulator


class SimulatorTests(unittest.TestCase):
    def test_airflow_units_and_four_stroke_cycle(self):
        sim = Rotax915Simulator()
        sim.state.rpm = 5800
        sim.state.manifold_pressure = 1520
        sim.state.manifold_temperature = 40
        sim._compute_airflow()
        expected = (152000 / (287 * 313.15)) * .001352 * (5800 / 120) * .8
        self.assertAlmostEqual(sim.state.airflow, expected)
        self.assertGreater(sim.state.airflow, .08)

    def test_power_anchors_fuel_energy_and_altitude(self):
        sim = Rotax915Simulator()
        sim.state.throttle_position = 1
        sim.state.oil_temperature = 100
        sim.state.operating_mode = 'POWER'
        for rpm, power in [(5500, 99), (5800, 104)]:
            sim.state.rpm = rpm
            sim._compute_expected_power()
            sim._compute_fuel_flow()
            self.assertAlmostEqual(sim.state.expected_power, power)
            efficiency = power / (sim.state.expected_fuel_flow * 32 / 3.6)
            self.assertTrue(.2 < efficiency < .4)
        sim.state.altitude = 23000
        sim._compute_expected_power()
        self.assertLess(sim.state.expected_power, 104)
        self.assertAlmostEqual(sim._altitude_to_pressure(15000), 571.835, places=2)

    def test_fault_windows_labels_and_timestep(self):
        for dt in (1, 30, 60, 120):
            sim = Rotax915Simulator(dt=dt, duration=240)
            sim.inject_fault('oil_degradation', .6, 0)
            df = sim.run()
            self.assertAlmostEqual(sim.fault.oil_degradation, .6)
            self.assertEqual(df.iloc[-1].fault_severity, .6)
            self.assertEqual(df.iloc[-1].fault_type, 'oil_degradation')
        sim = Rotax915Simulator(duration=200)
        sim.inject_fault('oil_degradation', .6, 10, 100)
        df = sim.run().set_index('time_s')
        self.assertEqual(df.loc[10, 'fault_severity'], 0)
        self.assertEqual(df.loc[10, 'fault_active'], 1)
        self.assertEqual(df.loc[110, 'fault_type'], 'none')
        self.assertEqual(sim.fault.oil_degradation, 0)

    def test_combined_and_repeated_events_retain_windows(self):
        sim = Rotax915Simulator(duration=400)
        sim.inject_faults([('bearing_wear', .2, 0, 100),
                           ('bearing_wear', .8, 200, 100),
                           ('oil_degradation', .5, 250, 100)])
        df = sim.run().set_index('time_s')
        self.assertEqual(df.loc[80, 'fault_severity'], .2)
        self.assertEqual(df.loc[150, 'fault_type'], 'none')
        self.assertEqual(df.loc[270, 'fault_type'], 'combined')
        self.assertEqual(df.loc[320, 'fault_type'], 'oil_degradation')
        self.assertEqual(df.loc[350, 'fault_type'], 'none')

    def test_sensor_bias_is_measurement_only_and_correct_channel(self):
        def run(fault=None):
            sim = Rotax915Simulator(duration=100, seed=71)
            if fault:
                sim.inject_fault(*fault)
            return sim.run()
        healthy = run()
        drift = run(('sensor_drift', .4, 0))
        self.assertEqual(drift.iloc[-1].ambient_temperature_c - healthy.iloc[-1].ambient_temperature_c, 4)
        for column in ('manifold_temperature_c', 'oil_temperature_c', 'expected_power_kw', 'egt_1_c'):
            pd.testing.assert_series_equal(healthy[column], drift[column])
        for sensor in range(1, 5):
            fault = run(('egt_sensor_fault', 1, 0, float('inf'), sensor))
            for channel in range(1, 5):
                diff = fault.iloc[-1][f'egt_{channel}_c'] - healthy.iloc[-1][f'egt_{channel}_c']
                self.assertAlmostEqual(diff, 75 if channel == sensor else 0)
        sim = Rotax915Simulator(seed=71, duration=100)
        sim.inject_faults([('egt_sensor_fault', 1, 0, 200, 1), ('egt_sensor_fault', .5, 0, 200, 4)])
        row = sim.run().iloc[-1]
        self.assertEqual(json.loads(row.active_faults), ['egt_sensor_fault:1', 'egt_sensor_fault:4'])

    def test_temperature_limits_are_not_clamps_and_large_dt_is_stable(self):
        sim = Rotax915Simulator(dt=1000)
        sim.state.rpm = 5800
        sim.state.throttle_position = 1
        sim.state.ambient_temperature = 50
        sim.fault.oil_degradation = 1
        sim.fault.coolant_leak = 1
        sim._compute_oil_temperature()
        sim._compute_coolant_temperature()
        self.assertTrue(130 < sim.state.oil_temperature <= 175)
        self.assertTrue(120 < sim.state.coolant_temperature <= 175)

    def test_injector_fault_cannot_raise_egt_at_idle(self):
        healthy = Rotax915Simulator(seed=12, duration=100).run()
        sim = Rotax915Simulator(seed=12, duration=100)
        sim.inject_fault('injector_degradation', .5)
        fault = sim.run()
        for channel in range(1, 5):
            col = f'egt_{channel}_c'
            self.assertAlmostEqual(healthy.iloc[-1][col] - fault.iloc[-1][col], 30)

    def test_mission_altitude_and_power_mode(self):
        mission = prepare_mission(12600, np.random.default_rng(42), vary=False)
        sim = Rotax915Simulator(duration=12600, dt=5, seed=42)
        sim.set_mission_profile(mission)
        df = sim.run()
        self.assertAlmostEqual(sum(p['duration'] for p in mission), 12600)
        self.assertLess(df.altitude_ft.diff().max() / 5 * 60, 4000)
        self.assertEqual(df[df.mission_phase == 'high_load'].iloc[-1].operating_mode, 'POWER')
        self.assertLess((df.mission_phase == 'landing').mean(), .02)
        self.assertGreater(df[(df.time_s >= 3600) & (df.time_s <= 4200)].altitude_ft.min(), 0)

    def test_partial_last_step_and_invalid_input(self):
        sim = Rotax915Simulator(dt=3, duration=10)
        self.assertEqual(sim.run().time_s.tolist(), [3, 6, 9, 10])
        with self.assertRaises(ValueError):
            sim.run()
        for dt in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                Rotax915Simulator(dt=dt)
        with self.assertRaises(ValueError):
            Rotax915Simulator().inject_fault('egt_sensor_fault', 3)


class GeneratorTests(unittest.TestCase):
    def test_reproducible_grouped_runs_and_provenance(self):
        with contextlib.redirect_stdout(io.StringIO()):
            df, meta = run_all_scenarios(dt=60, seed=19, runs_per_scenario=2)
            other, _ = run_all_scenarios(dt=60, seed=19, runs_per_scenario=2)
        pd.testing.assert_frame_equal(df, other)
        self.assertEqual(len(meta['scenarios']), 2 * len(SCENARIOS))
        self.assertEqual(df.run_id.nunique(), 2)
        self.assertEqual(meta['split_group_column'], 'run_id')
        self.assertFalse(set(FEATURE_COLUMNS) & set(meta['label_columns']))
        self.assertNotIn('scenario_name', FEATURE_COLUMNS)
        self.assertNotIn('time_s', FEATURE_COLUMNS)
        self.assertEqual(len(meta['source_sha256']['simulator']), 64)
        self.assertIn('events', meta['scenarios'][1])
        self.assertNotEqual(meta['scenarios'][0]['mission_profile'], meta['scenarios'][12]['mission_profile'])
        json.dumps(meta, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
