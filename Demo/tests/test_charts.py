"""Regression checks for visible telemetry evidence and reference overlays."""

import json
from pathlib import Path
import sys
import unittest

from streamlit.testing.v1 import AppTest

DEMO_DIR = Path(__file__).resolve().parents[1]
if str(DEMO_DIR) not in sys.path:
    sys.path.insert(0, str(DEMO_DIR))

from components.statistics_table import build_statistics_table
from clustering.visualizer import _analysis_inputs
from config.scenarios import FLIGHT_STAGES, NOMINAL_SCENARIO
from telemetry.generator import generate_telemetry_data


class SensorStatisticsTests(unittest.TestCase):
    def setUp(self):
        self.bundle = generate_telemetry_data(NOMINAL_SCENARIO, noise_level=0, flight_stage=FLIGHT_STAGES[3])
        self.df = self.bundle["df"].copy(deep=True)

    def test_single_spike_is_counted_even_when_mean_is_within_reference(self):
        column = "Oil Pressure (bar)"
        band = self.df.attrs["reference_bands"][column]
        self.df.loc[10, column] = band["min"] - 0.5
        summary = build_statistics_table(self.df, self.bundle["baseline_df"])
        oil = summary.set_index("Sensor").loc["Oil pressure"]
        self.assertEqual(oil["Excursions"], 1)
        self.assertGreater(oil["Mean"], band["min"])
        self.assertLess(oil["Mean"], band["max"])
        self.assertEqual(oil["Minimum"], band["min"] - 0.5)
        self.assertEqual(oil["Latest Δ nominal"], 0)

    def test_every_cylinder_has_independent_excursion_counts(self):
        for cylinder in range(1, 5):
            column = f"EGT Cyl {cylinder} (°C)"
            band = self.df.attrs["reference_bands"][column]
            self.df.loc[cylinder, column] = band["max"] + 1 if cylinder % 2 else band["min"] - 1
        summary = build_statistics_table(self.df).set_index("Sensor")
        for cylinder in range(1, 5):
            with self.subTest(cylinder=cylinder):
                self.assertEqual(summary.loc[f"EGT cylinder {cylinder}", "Excursions"], 1)
        self.assertIn("EGT cylinder spread", summary.index)

    def test_nominal_stage_windows_do_not_use_cruise_or_global_bounds(self):
        for stage in FLIGHT_STAGES:
            with self.subTest(stage=stage):
                bundle = generate_telemetry_data(NOMINAL_SCENARIO, noise_level=0, flight_stage=stage)
                summary = build_statistics_table(bundle["df"], bundle["baseline_df"])
                self.assertEqual(int(summary["Excursions"].sum()), 0)


class ChartRenderingTests(unittest.TestCase):
    def test_fallback_respects_exact_reference_edges_and_flags_real_departures(self):
        for stage in FLIGHT_STAGES:
            with self.subTest(stage=stage):
                bundle = generate_telemetry_data(NOMINAL_SCENARIO, noise_level=0, flight_stage=stage)
                df = bundle["df"].copy(deep=True)
                for column, band in df.attrs["reference_bands"].items():
                    df.loc[10, column] = band["min"]
                    df.loc[11, column] = band["max"]
                df.loc[12, "Fuel Pressure (bar)"] = df.attrs["reference_bands"]["Fuel Pressure (bar)"]["max"] + 0.01
                _, _, scores, flags = _analysis_inputs(df, bundle["baseline_df"], None, None)
                self.assertFalse(flags[10])
                self.assertFalse(flags[11])
                self.assertEqual(scores[10], 1)
                self.assertEqual(scores[11], 1)
                self.assertEqual(int(flags.sum()), 1)
                self.assertTrue(flags[12])
                self.assertGreater(scores[12], 1)

    def test_nominal_overlay_toggle_and_sensor_table_render(self):
        app = AppTest.from_string('''
import streamlit as st
from config.scenarios import NOMINAL_SCENARIO, FLIGHT_STAGES
from telemetry.generator import generate_telemetry_data
from components.charts import render_telemetry_charts
from components.statistics_table import render_statistics_table
bundle = generate_telemetry_data(NOMINAL_SCENARIO, noise_level=0, flight_stage=FLIGHT_STAGES[0])
show = st.checkbox("Show nominal", value=True)
render_telemetry_charts(bundle["df"], NOMINAL_SCENARIO, bundle["baseline_df"], show_baseline=show)
render_statistics_table(bundle["df"], bundle["baseline_df"])
''').run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        figures = [json.loads(element.proto.spec) for element in app.get("plotly_chart")]
        self.assertEqual([len(figure["data"]) for figure in figures], [5, 4, 4, 4])
        self.assertEqual(len(app.dataframe), 1)
        # A warm-up CHT reference must follow the stage (57–73), not cruise.
        self.assertIn(57, [shape["y0"] for shape in figures[2]["layout"]["shapes"]])
        app.checkbox[0].uncheck().run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        figures = [json.loads(element.proto.spec) for element in app.get("plotly_chart")]
        self.assertEqual([len(figure["data"]) for figure in figures], [4, 2, 2, 2])
        self.assertFalse(any("Nominal" in trace["name"] for figure in figures for trace in figure["data"]))

    def test_analysis_uses_measured_sample_flags(self):
        app = AppTest.from_string('''
from config.scenarios import NOMINAL_SCENARIO, FLIGHT_STAGES
from telemetry.generator import generate_telemetry_data, score_telemetry
from clustering.visualizer import render_clustering_visualizer
bundle = generate_telemetry_data(NOMINAL_SCENARIO, noise_level=0, flight_stage=FLIGHT_STAGES[3])
df = bundle["df"].copy(deep=True)
df.loc[10, "Oil Pressure (bar)"] = 2.5
analysis = score_telemetry(df, FLIGHT_STAGES[3])
render_clustering_visualizer(df, False, NOMINAL_SCENARIO, bundle["baseline_df"], analysis["anomaly_scores"], analysis["outlier_mask"])
''').run(timeout=20)
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.get("plotly_chart")), 2)
        self.assertEqual(app.metric[0].value, "1 / 30")
        self.assertEqual(app.metric[2].value, "10 s")
        self.assertTrue(any("Oil pressure" in element.value for element in app.markdown))


if __name__ == "__main__":
    unittest.main()
