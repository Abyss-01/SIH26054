"""Regression checks for synthetic data, measured scoring and the flight tour."""

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from Demo.config.engine_specs import stage_reference_bands
from Demo.config.scenarios import (
    AUTO_SCENARIO, FLIGHT_STAGES, NOMINAL_SCENARIO, SCENARIO_OPTIONS,
    resolve_scenario, stage_at_distance,
)
from Demo.telemetry.generator import EGT_COLUMNS, generate_telemetry_data, score_telemetry


class FlightTourTests(unittest.TestCase):
    def test_stage_boundaries(self):
        boundaries = (20, 50, 110, 180, 240, 280, 300)
        self.assertEqual(stage_at_distance(0), FLIGHT_STAGES[0])
        for index, boundary in enumerate(boundaries):
            self.assertEqual(stage_at_distance(boundary), FLIGHT_STAGES[index])
            if boundary < 300:
                self.assertEqual(stage_at_distance(boundary + 0.01), FLIGHT_STAGES[index + 1])

    def test_auto_tour_and_manual_override(self):
        expected = [NOMINAL_SCENARIO, NOMINAL_SCENARIO, *[SCENARIO_OPTIONS[i] for i in (3, 2, 5, 8, 7)]]
        for stage, scenario in zip(FLIGHT_STAGES, expected):
            self.assertEqual(resolve_scenario(AUTO_SCENARIO, stage), scenario)
            self.assertEqual(generate_telemetry_data(AUTO_SCENARIO, flight_stage=stage)["scenario_key"], scenario)
            for manual in SCENARIO_OPTIONS[1:]:
                self.assertEqual(resolve_scenario(manual, stage), manual)

    def test_invalid_tour_inputs_are_rejected(self):
        for distance in (-1, 301, float("nan"), float("inf"), "140", None, True):
            with self.subTest(distance=distance), self.assertRaises(ValueError):
                stage_at_distance(distance)
        for scenario, stage in (("unknown", FLIGHT_STAGES[0]), (AUTO_SCENARIO, "unknown"), ([], FLIGHT_STAGES[0])):
            with self.subTest(scenario=scenario, stage=stage), self.assertRaises(ValueError):
                resolve_scenario(scenario, stage)


class TelemetryTests(unittest.TestCase):
    def test_reproducible_with_seed_and_new_seed_changes_noise(self):
        first = generate_telemetry_data(SCENARIO_OPTIONS[2], seed=100)
        again = generate_telemetry_data(SCENARIO_OPTIONS[2], seed=100)
        different = generate_telemetry_data(SCENARIO_OPTIONS[2], seed=101)
        assert_frame_equal(first["df"], again["df"])
        assert_frame_equal(first["baseline_df"], again["baseline_df"])
        np.testing.assert_array_equal(first["anomaly_scores"], again["anomaly_scores"])
        self.assertFalse(first["df"].equals(different["df"]))

    def test_does_not_change_global_random_state(self):
        before = np.random.get_state()
        generate_telemetry_data(SCENARIO_OPTIONS[7], seed=108)
        after = np.random.get_state()
        self.assertEqual(before[0], after[0])
        np.testing.assert_array_equal(before[1], after[1])
        self.assertEqual(before[2:], after[2:])

    def test_zero_noise_is_seed_independent(self):
        for scenario in SCENARIO_OPTIONS[1:]:
            with self.subTest(scenario=scenario):
                assert_frame_equal(
                    generate_telemetry_data(scenario, noise_level=0, seed=1)["df"],
                    generate_telemetry_data(scenario, noise_level=0, seed=2)["df"],
                )

    def test_nominal_baseline_matches_all_flight_stages(self):
        for stage in FLIGHT_STAGES:
            with self.subTest(stage=stage):
                telemetry = generate_telemetry_data(NOMINAL_SCENARIO, flight_stage=stage)
                assert_frame_equal(telemetry["df"], telemetry["baseline_df"])
                self.assertFalse(telemetry["is_outlier"])
                self.assertEqual(telemetry["outlier_count"], 0)
                self.assertEqual(telemetry["status_label"], "NORMAL")
                self.assertIsNone(telemetry["rul"])

    def test_faults_are_detected_in_every_stage(self):
        for stage in FLIGHT_STAGES:
            for scenario in SCENARIO_OPTIONS[2:]:
                for noise in (0, 1, 2):
                    with self.subTest(stage=stage, scenario=scenario, noise=noise):
                        telemetry = generate_telemetry_data(scenario, noise, stage)
                        self.assertTrue(telemetry["is_outlier"])
                        self.assertGreater(telemetry["outlier_count"], 0)
                        self.assertLess(telemetry["outlier_count"], len(telemetry["df"]))
                        self.assertTrue(np.isfinite(telemetry["df"].to_numpy()).all())
                        self.assertTrue(0 <= telemetry["health"] <= 100)
                        np.testing.assert_array_equal(
                            telemetry["outlier_mask"],
                            telemetry["anomaly_scores"] > telemetry["anomaly_threshold"],
                        )

    def test_baseline_is_same_seed_nominal_with_delayed_injection(self):
        nominal = generate_telemetry_data(NOMINAL_SCENARIO, seed=64)
        for scenario in SCENARIO_OPTIONS[2:]:
            with self.subTest(scenario=scenario):
                telemetry = generate_telemetry_data(scenario, seed=64)
                assert_frame_equal(telemetry["baseline_df"], nominal["df"])
                assert_frame_equal(telemetry["df"].iloc[:8], nominal["df"].iloc[:8])
                self.assertFalse(telemetry["df"].iloc[8:].equals(nominal["df"].iloc[8:]))

    def test_scores_follow_measurements_without_a_scenario_label(self):
        nominal = generate_telemetry_data(NOMINAL_SCENARIO, noise_level=0)
        changed = nominal["df"].copy()
        changed.loc[12, "Oil Pressure (bar)"] = 1.0
        result = score_telemetry(changed, FLIGHT_STAGES[3])
        self.assertEqual(result["outlier_count"], 1)
        self.assertTrue(result["outlier_mask"][12])
        self.assertLess(result["health"], nominal["health"])
        self.assertEqual(result["status_label"], "WARNING")
        repaired = score_telemetry(nominal["df"], FLIGHT_STAGES[3])
        self.assertEqual(repaired["status_label"], "NORMAL")
        self.assertFalse(repaired["is_outlier"])

    def test_exact_reference_edges_are_inclusive(self):
        telemetry = generate_telemetry_data(NOMINAL_SCENARIO, noise_level=0)
        df = telemetry["df"].copy()
        band = telemetry["reference_bands"]["Fuel Pressure (bar)"]
        df.loc[0, "Fuel Pressure (bar)"] = band["max"]
        df.loc[1, "Fuel Pressure (bar)"] = band["min"]
        df.loc[2, "Fuel Pressure (bar)"] = band["max"] + 0.01
        result = score_telemetry(df, FLIGHT_STAGES[3])
        self.assertEqual(result["outlier_count"], 1)
        self.assertTrue(result["outlier_mask"][2])
        np.testing.assert_array_equal(result["outlier_mask"], result["anomaly_scores"] > 1)

    def test_nominal_high_noise_can_be_flagged(self):
        telemetry = generate_telemetry_data(NOMINAL_SCENARIO, noise_level=5)
        self.assertTrue(telemetry["is_outlier"])
        self.assertLess(telemetry["health"], 100)

    def test_egt_spread_and_average_are_measured_from_cylinders(self):
        telemetry = generate_telemetry_data(SCENARIO_OPTIONS[6])
        df = telemetry["df"]
        spread = (df[EGT_COLUMNS].max(axis=1) - df[EGT_COLUMNS].min(axis=1)).round(1)
        np.testing.assert_array_equal(df["EGT Spread (°C)"], spread)
        np.testing.assert_array_equal(df["EGT Avg (°C)"], df[EGT_COLUMNS].mean(axis=1).round(1))
        self.assertEqual(telemetry["peak_egt_spread"], spread.max())
        self.assertLess(spread.max(), 200)

    def test_result_contract_and_mutable_data_are_independent(self):
        telemetry = generate_telemetry_data(NOMINAL_SCENARIO)
        self.assertEqual(len(telemetry["df"]), 30)
        self.assertEqual(telemetry["outlier_mask"].shape, (30,))
        self.assertEqual(telemetry["outlier_mask"].dtype, np.dtype(bool))
        self.assertEqual(telemetry["anomaly_scores"].dtype, np.dtype(float))
        self.assertEqual(telemetry["df"].attrs["flight_stage"], FLIGHT_STAGES[3])
        self.assertEqual(telemetry["df"].attrs["reference_bands"], telemetry["reference_bands"])
        telemetry["df"].loc[0, "Oil Pressure (bar)"] = 99
        self.assertNotEqual(telemetry["baseline_df"].loc[0, "Oil Pressure (bar)"], 99)
        telemetry["reference_bands"]["CHT (°C)"]["max"] = 999
        self.assertNotEqual(stage_reference_bands(FLIGHT_STAGES[3])["CHT (°C)"]["max"], 999)

    def test_invalid_generator_inputs_are_rejected(self):
        invalid = [
            {"scenario_key": "unknown"}, {"scenario_key": []}, {"flight_stage": "unknown"},
            {"noise_level": -1}, {"noise_level": 6}, {"noise_level": float("nan")},
            {"noise_level": float("inf")}, {"noise_level": "1"}, {"noise_level": True},
            {"seed": -1}, {"seed": 2**32}, {"seed": 1.5}, {"seed": True}, {"seed": None},
        ]
        for overrides in invalid:
            arguments = {"scenario_key": NOMINAL_SCENARIO, **overrides}
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                generate_telemetry_data(**arguments)

    def test_invalid_measurements_are_rejected(self):
        df = generate_telemetry_data(NOMINAL_SCENARIO)["df"]
        invalid = [df.iloc[:0], df.drop(columns=["CHT (°C)"]), df.assign(**{"CHT (°C)": float("nan")})]
        for frame in invalid:
            with self.subTest(columns=frame.columns, length=len(frame)), self.assertRaises(ValueError):
                score_telemetry(frame, FLIGHT_STAGES[3])


if __name__ == "__main__":
    unittest.main()
