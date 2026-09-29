"""Exercise the complete console and its session state without a browser/API."""

from pathlib import Path
import sys
import time
import unittest

from pandas.testing import assert_frame_equal
from streamlit.testing.v1 import AppTest

DEMO_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(DEMO_DIR))

from Demo.config.scenarios import AUTO_SCENARIO, FLIGHT_STAGES, SCENARIO_LABELS, SCENARIO_OPTIONS
from Demo.telemetry.generator import generate_telemetry_data


def button(app, label):
    return next(item for item in app.button if item.label == label)


def raw_telemetry(app):
    return next(item.value for item in app.dataframe if "Time (s)" in item.value.columns)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(DEMO_DIR / "app.py"), default_timeout=15)
        self.app.session_state["gemini_api_key"] = ""
        self.app.run()
        self.assert_no_error()

    def assert_no_error(self):
        self.assertFalse(self.app.exception, [item.message for item in self.app.exception])

    def click(self, label):
        button(self.app, label).click().run()
        self.assert_no_error()

    def assert_snapshot(self, scenario, stage, *, noise=1.0, seed=42):
        expected = generate_telemetry_data(scenario, noise_level=noise, flight_stage=stage, seed=seed)
        # Streamlit's Arrow conversion does not preserve DataFrame attrs.
        assert_frame_equal(raw_telemetry(self.app), expected["df"])
        self.assertTrue(any(SCENARIO_LABELS[expected["scenario_key"]] in item.value for item in self.app.markdown))

    def test_startup_and_every_manual_scenario(self):
        self.assertEqual(self.app.session_state["flight_distance"], 140)
        self.assertEqual(self.app.session_state["sample_seed"], 42)
        self.assertEqual(len(raw_telemetry(self.app)), 30)
        self.assertEqual([tab.label for tab in self.app.tabs], ["Telemetry", "AI Diagnostics", "Table Summary", "Anomaly Analysis"])
        self.assert_snapshot(AUTO_SCENARIO, FLIGHT_STAGES[3])
        for scenario in SCENARIO_OPTIONS[1:]:
            with self.subTest(scenario=scenario):
                self.app.selectbox(key="manual_scenario").set_value(scenario).run()
                self.assert_no_error()
                self.assertEqual(self.app.session_state["manual_scenario"], scenario)
                self.assert_snapshot(scenario, FLIGHT_STAGES[3])

    def test_guided_tour_previous_next_and_disabled_endpoints(self):
        for expected_distance, stage in ((80, 2), (35, 1), (10, 0)):
            self.click("← Previous")
            self.assertEqual(self.app.session_state["flight_distance"], expected_distance)
            self.assert_snapshot(AUTO_SCENARIO, FLIGHT_STAGES[stage])
        self.assertTrue(button(self.app, "← Previous").disabled)
        for expected_distance, stage in ((35, 1), (80, 2), (145, 3), (210, 4), (260, 5), (295, 6)):
            self.click("Next →")
            self.assertEqual(self.app.session_state["flight_distance"], expected_distance)
            self.assert_snapshot(AUTO_SCENARIO, FLIGHT_STAGES[stage])
        self.assertTrue(button(self.app, "Next →").disabled)

    def test_mission_slider_resolves_each_stage_boundary(self):
        cases = ((0, 0), (20, 0), (25, 1), (50, 1), (55, 2), (110, 2),
                 (115, 3), (180, 3), (185, 4), (240, 4), (245, 5),
                 (280, 5), (285, 6), (300, 6))
        for distance, stage in cases:
            with self.subTest(distance=distance):
                self.app.slider(key="flight_distance").set_value(distance).run()
                self.assert_no_error()
                self.assertEqual(self.app.session_state["flight_distance"], distance)
                self.assert_snapshot(AUTO_SCENARIO, FLIGHT_STAGES[stage])

    def test_new_snapshot_is_reproducible_and_reset_restores_defaults(self):
        original = raw_telemetry(self.app).copy()
        self.click("New snapshot")
        self.assertEqual(self.app.session_state["sample_seed"], 43)
        self.assertFalse(original.equals(raw_telemetry(self.app)))
        self.assert_snapshot(AUTO_SCENARIO, FLIGHT_STAGES[3], seed=43)
        refreshed = raw_telemetry(self.app).copy()
        self.app.run()
        self.assert_no_error()
        assert_frame_equal(raw_telemetry(self.app), refreshed)
        self.app.selectbox(key="manual_scenario").set_value(SCENARIO_OPTIONS[7])
        self.app.slider(key="noise_level").set_value(1.8)
        self.app.slider(key="flight_distance").set_value(260)
        self.app.checkbox(key="show_baseline").uncheck().run()
        self.click("Reset demo")
        defaults = {"manual_scenario": AUTO_SCENARIO, "noise_level": 1.0, "flight_distance": 140,
                    "sample_seed": 42, "show_baseline": True, "mission_playing": False}
        for key, value in defaults.items():
            self.assertEqual(self.app.session_state[key], value, key)
        assert_frame_equal(raw_telemetry(self.app), original)

    def test_settings_roundtrip_preserves_mission_controls_and_snapshot(self):
        self.app.selectbox(key="manual_scenario").set_value(SCENARIO_OPTIONS[6])
        self.app.slider(key="noise_level").set_value(1.7)
        self.app.slider(key="flight_distance").set_value(260)
        self.app.checkbox(key="show_baseline").uncheck().run()
        self.click("New snapshot")
        controls = {key: self.app.session_state[key] for key in
                    ("manual_scenario", "noise_level", "flight_distance", "sample_seed", "show_baseline")}
        snapshot = raw_telemetry(self.app).copy()
        for return_method in ("sidebar", "button"):
            with self.subTest(return_method=return_method):
                self.app.radio(key="active_page").set_value("settings").run()
                self.assert_no_error()
                self.assertEqual(self.app.session_state["active_page"], "settings")
                self.assertFalse(self.app.session_state["mission_playing"])
                self.assertFalse(self.app.selectbox)
                if return_method == "sidebar":
                    self.app.radio(key="active_page").set_value("dashboard").run()
                else:
                    self.click("Return to Dashboard")
                self.assert_no_error()
                for key, value in controls.items():
                    self.assertEqual(self.app.session_state[key], value, key)
                self.assertEqual(self.app.radio(key="active_page").value, "dashboard")
                self.assertEqual(self.app.selectbox(key="manual_scenario").value, controls["manual_scenario"])
                self.assertFalse(self.app.checkbox(key="show_baseline").value)
                assert_frame_equal(raw_telemetry(self.app), snapshot)

    def test_play_pause_and_mission_completion_without_sleep(self):
        self.click("Play mission")
        self.assertTrue(self.app.session_state["mission_playing"])
        distance = self.app.session_state["flight_distance"]
        self.app.session_state["last_mission_tick"] = time.monotonic() - 10
        self.app.run()
        self.assert_no_error()
        self.assertEqual(self.app.session_state["flight_distance"], distance + 5)
        self.assertTrue(self.app.session_state["mission_playing"])
        self.click("Pause mission")
        self.assertFalse(self.app.session_state["mission_playing"])
        paused_distance = self.app.session_state["flight_distance"]
        self.app.session_state["last_mission_tick"] = time.monotonic() - 10
        self.app.run()
        self.assertEqual(self.app.session_state["flight_distance"], paused_distance)

        self.app.slider(key="flight_distance").set_value(295).run()
        self.click("Play mission")
        self.app.session_state["last_mission_tick"] = time.monotonic() - 10
        self.app.run()
        self.assert_no_error()
        self.assertEqual(self.app.session_state["flight_distance"], 300)
        self.assertFalse(self.app.session_state["mission_playing"])
        self.assertTrue(button(self.app, "Next →").disabled)
        self.assert_snapshot(AUTO_SCENARIO, FLIGHT_STAGES[6])
        self.click("Play mission")
        self.assertEqual(self.app.session_state["flight_distance"], 0)
        self.assertTrue(self.app.session_state["mission_playing"])

    def test_manual_controls_and_navigation_pause_playback(self):
        self.click("Play mission")
        self.app.slider(key="flight_distance").set_value(200).run()
        self.assertFalse(self.app.session_state["mission_playing"])
        self.click("Play mission")
        self.app.selectbox(key="manual_scenario").set_value(SCENARIO_OPTIONS[7]).run()
        self.assertFalse(self.app.session_state["mission_playing"])
        self.click("Play mission")
        self.app.slider(key="noise_level").set_value(1.4).run()
        self.assertFalse(self.app.session_state["mission_playing"])
        self.click("Play mission")
        self.click("New snapshot")
        self.assertFalse(self.app.session_state["mission_playing"])
        self.click("Play mission")
        self.app.radio(key="active_page").set_value("settings").run()
        self.assert_no_error()
        self.assertFalse(self.app.session_state["mission_playing"])


if __name__ == "__main__":
    unittest.main()
