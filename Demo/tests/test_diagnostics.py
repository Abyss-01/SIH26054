"""Regressions for evidence accuracy, optional API behavior, and session state."""

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from Demo.ai_engine import copilot
from Demo.views import settings
from Demo.ai_engine.errors import describe_gemini_error


class ProviderFailure(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message
        super().__init__(message)


class ErrorExplanationTests(unittest.TestCase):
    def test_provider_failures_are_distinguished_without_exposing_payloads(self):
        for code, message, expected in (
            (400, "API key not valid: private-key", "API key rejected"),
            (403, "private-key cannot access this project", "Access denied"),
            (429, "quota exhausted: private-key", "Quota or rate limit reached"),
            (404, "private-key model not found", "Model or endpoint unavailable"),
            (503, "private-key service unavailable", "Google service error"),
        ):
            with self.subTest(code=code):
                explanation = describe_gemini_error(ProviderFailure(code, message))
                self.assertEqual(explanation["http_code"], code)
                self.assertEqual(explanation["title"], expected)
                self.assertNotIn("private-key", str(explanation))

    def test_transport_and_unknown_failures_do_not_expose_request_urls(self):
        for failure, expected in (
            (TimeoutError("https://example.test?key=private-key"), "Request timed out"),
            (ConnectionError("https://example.test?key=private-key"), "Network connection failed"),
            (RuntimeError("https://example.test?key=private-key"), "Client request failed"),
        ):
            result = describe_gemini_error(failure)
            self.assertIsNone(result["http_code"])
            self.assertEqual(result["title"], expected)
            self.assertNotIn("private-key", str(result))
            self.assertNotIn("example.test", str(result))


def sample_frame():
    return pd.DataFrame({
        "Time (s)": [0, 1, 2],
        "Oil Pressure (bar)": [4.0, 3.0, 1.0],
        "Engine RPM": [5000, 5100, 4800],
        "EGT Cyl 1 (°C)": [700, 710, 720],
        "EGT Cyl 2 (°C)": [720, 750, 800],
        "EGT Cyl 3 (°C)": [710, 720, 730],
        "EGT Cyl 4 (°C)": [705, 715, 725],
        "EGT Spread (°C)": [999, 999, 999],
    })


def generate(frame=None):
    return copilot.generate_ai_diagnosis(
        "6. Oil Pressure Loss / Lubrication Degradation",
        sample_frame() if frame is None else frame,
        31.2, None, "Demo outlier", "4. Cruise",
    )


class EvidenceTests(unittest.TestCase):
    def test_selected_model_controls_requests_and_report_identity(self):
        state = {"gemini_model": "models/gemini-3.8-flash"}
        client = Mock()
        client.models.generate_content.return_value = SimpleNamespace(text="Connected")
        with patch.object(copilot.st, "session_state", state), \
                patch.object(copilot, "create_gemini_client", return_value=client):
            first = copilot.api_configuration_id("fake-key")
            self.assertEqual(copilot.request_gemini_text("fake-key", "ping"), "Connected")
            client.models.generate_content.assert_called_once_with(model="gemini-3.8-flash", contents="ping")
            state["gemini_model"] = "gemini-another-text-model"
            self.assertNotEqual(first, copilot.api_configuration_id("fake-key"))
        client.close.assert_called_once()

    def test_model_discovery_filters_generation_support_and_closes_client(self):
        client = Mock()
        client.models.list.return_value = [
            SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-embedding", supported_actions=["embedContent"]),
            SimpleNamespace(name="models/gemini-text", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/other", supported_actions=["generateContent"]),
        ]
        with patch.object(copilot, "create_gemini_client", return_value=client):
            self.assertEqual(copilot.list_gemini_models("fake-key"), ["gemini-3.8-flash", "gemini-text"])
        client.close.assert_called_once()

    def test_model_discovery_closes_client_on_api_error(self):
        client = Mock()
        client.models.list.side_effect = ProviderFailure(403, "denied")
        with patch.object(copilot, "create_gemini_client", return_value=client):
            with self.assertRaises(ProviderFailure):
                copilot.list_gemini_models("fake-key")
        client.close.assert_called_once()

    def test_actual_range_delta_and_simultaneous_cylinder_spread(self):
        summary = copilot.summarize_telemetry(sample_frame())
        oil = summary["Oil Pressure (bar)"]
        self.assertEqual((oil["min"], oil["max"], oil["change"]), (1, 4, -3))
        self.assertAlmostEqual(oil["mean"], 8 / 3)
        spread = summary["EGT Spread (°C)"]
        self.assertEqual((spread["min"], spread["max"]), (20, 80))

    def test_nonfinite_values_are_excluded(self):
        frame = pd.DataFrame({"Oil Pressure (bar)": [np.nan, 4, np.inf, 2]})
        summary = copilot.summarize_telemetry(frame)["Oil Pressure (bar)"]
        self.assertEqual(summary["samples"], 2)
        self.assertEqual(summary["change"], -2)
        self.assertEqual(summary["mean"], 3)

    def test_snapshot_changes_with_data_context_and_api_settings(self):
        args = ["nominal", sample_frame(), 90, None, "nominal", "4. Cruise", ""]
        original = copilot.snapshot_fingerprint(*args)
        self.assertEqual(original, copilot.snapshot_fingerprint(*args))
        for index, replacement in [(0, "fault"), (2, 60), (4, "outlier"),
                                    (5, "3. Climb"), (6, "different-key")]:
            changed = args.copy()
            changed[index] = replacement
            self.assertNotEqual(original, copilot.snapshot_fingerprint(*changed))
        changed_frame = sample_frame()
        changed_frame.loc[1, "Oil Pressure (bar)"] = 2.5
        args[1] = changed_frame
        self.assertNotEqual(original, copilot.snapshot_fingerprint(*args))

    def test_report_uses_observed_evidence_without_life_or_manual_claims(self):
        with patch.object(copilot.st, "session_state", {}), \
                patch.object(copilot, "request_gemini_text") as request:
            report, live = generate()
        request.assert_not_called()
        self.assertFalse(live)
        self.assertIn("| Oil Pressure (bar) | 1.00 | 2.67 | 4.00 | -3.00 |", report)
        self.assertIn("3 samples · t = 0–2 s", report)
        self.assertIn("Synthetic simulation", report)
        self.assertNotIn("Manual Ref", report)
        self.assertNotIn("hours", report)
        self.assertNotIn("EMERGENCY", report)

    def test_missing_sdk_and_provider_failure_use_safe_local_fallback(self):
        for available in (False, True):
            with self.subTest(sdk_available=available), \
                    patch.object(copilot.st, "session_state", {"gemini_api_key": "private-key"}), \
                    patch.object(copilot, "GENAI_SDK_AVAILABLE", available), \
                    patch.object(copilot, "request_gemini_text", side_effect=RuntimeError("private-key leaked")) as request:
                report, live = generate()
            self.assertFalse(live)
            self.assertIn("Local evidence summary", report)
            self.assertNotIn("private-key", report)
            self.assertEqual(request.call_count, int(available))

    def test_gemini_response_is_labeled_and_request_is_grounded(self):
        with patch.object(copilot.st, "session_state", {"gemini_api_key": "fake-key"}), \
                patch.object(copilot, "GENAI_SDK_AVAILABLE", True), \
                patch.object(copilot, "request_gemini_text", return_value="A synthetic oil pressure decline.") as request:
            report, live = generate()
        self.assertTrue(live)
        self.assertIn("Analysis source:** Gemini", report)
        self.assertIn("A synthetic oil pressure decline.", report)
        self.assertIn("1.00 | 2.67 | 4.00", request.call_args.args[1])

    def test_client_timeout_and_cleanup_when_response_is_empty(self):
        events = {}

        class Client:
            def __init__(self, api_key, http_options=None):
                events.update(key=api_key, options=http_options)
                self.models = SimpleNamespace(generate_content=lambda **kwargs: SimpleNamespace(text=None))

            def close(self):
                events["closed"] = True

        with patch.object(copilot, "GENAI_SDK_AVAILABLE", True), \
                patch.object(copilot, "genai", SimpleNamespace(Client=Client)):
            with self.assertRaises(ValueError):
                copilot.request_gemini_text(" fake-key ", "test")
        self.assertEqual(events["options"], {"timeout": 15_000})
        self.assertEqual(events["key"], "fake-key")
        self.assertTrue(events["closed"])

    def test_empty_telemetry_is_handled_without_api_request(self):
        with patch.object(copilot, "request_gemini_text") as request:
            report, live = generate(pd.DataFrame())
        request.assert_not_called()
        self.assertFalse(live)
        self.assertIn("No finite telemetry", report)


REVIEW_APP = """
import pandas as pd
import streamlit as st
from Demo.ai_engine.copilot import render_ai_diagnostic_section
st.session_state.setdefault('gemini_api_key', '')
sample = st.slider('Snapshot', 0, 2, 0)
frame = pd.DataFrame({'Time (s)': [0, 1], 'Oil Pressure (bar)': [4.0, 3.0 - sample]})
render_ai_diagnostic_section('6. Oil Pressure Loss / Lubrication Degradation', frame, 70, None, 'Demo outlier', '4. Cruise')
"""

SETTINGS_APP = """
import streamlit as st
from Demo.views.settings import render_settings_view
st.session_state.setdefault('gemini_api_key', '')
st.radio('Navigation', ['dashboard', 'settings'], key='active_page')
if st.session_state['active_page'] == 'settings':
    render_settings_view()
else:
    st.write('Dashboard')
"""


def click_label(app, label):
    next(button for button in app.button if button.label == label).click().run()


class SessionTests(unittest.TestCase):
    def test_discovered_model_can_replace_missing_model_without_automatic_requests(self):
        with patch.object(settings, "GENAI_SDK_AVAILABLE", True), \
                patch.object(settings, "list_gemini_models", return_value=["gemini-available-text"]) as discover, \
                patch.object(settings, "request_gemini_text", return_value="Connected") as request:
            app = AppTest.from_string(SETTINGS_APP).run()
            app.radio[0].set_value("settings").run()
            app.text_input[0].set_value("fake-key")
            click_label(app, "Save key")
            discover.assert_not_called()
            request.assert_not_called()
            click_label(app, "Load available models")
            discover.assert_called_once_with("fake-key")
            request.assert_not_called()
            click_label(app, "Use selected model")
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["gemini_model"], "gemini-available-text")
            click_label(app, "Test connection")
            self.assertTrue(app.session_state["gemini_connection_status"]["ok"])
            app.text_input(key="gemini_model").set_value("gemini-different-model").run()
            self.assertFalse(app.exception)
            self.assertTrue(any("Not tested" in item.value for item in app.info))
            self.assertEqual(request.call_count, 1)

    def test_connection_failure_shows_reason_and_clears_on_success(self):
        with patch.object(settings, "GENAI_SDK_AVAILABLE", True), \
                patch.object(settings, "request_gemini_text", side_effect=ProviderFailure(429, "quota: private-key")) as request:
            app = AppTest.from_string(SETTINGS_APP).run()
            app.radio[0].set_value("settings").run()
            app.text_input[0].set_value("private-key")
            click_label(app, "Save key")
            click_label(app, "Test connection")
            self.assertFalse(app.exception)
            self.assertTrue(any("HTTP 429" in item.value for item in app.error))
            self.assertNotIn("private-key", str(app.session_state["gemini_connection_status"]))
            app.run()
            self.assertTrue(any("HTTP 429" in item.value for item in app.error))
            request.side_effect = None
            request.return_value = "Connection verified."
            click_label(app, "Test connection")
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertIsNone(app.session_state["gemini_connection_status"]["error"])
            self.assertTrue(any("Connection verified" in item.value for item in app.success))

    def test_running_review_pauses_playback_and_does_not_repeat_api_call(self):
        with patch.object(copilot, "GENAI_SDK_AVAILABLE", True), \
                patch.object(copilot, "request_gemini_text", return_value="Synthetic pattern review.") as request:
            app = AppTest.from_string(REVIEW_APP)
            app.session_state["gemini_api_key"] = "fake-key"
            app.session_state["mission_playing"] = True
            app.run()
            request.assert_not_called()
            click_label(app, "Generate telemetry review")
            self.assertFalse(app.exception)
            self.assertFalse(app.session_state["mission_playing"])
            request.assert_called_once()
            self.assertTrue(any("Synthetic pattern review." in item.value for item in app.markdown))
            app.run()
            request.assert_called_once()
            app.session_state["gemini_api_key"] = "new-key"
            app.run()
            self.assertFalse(any("Synthetic pattern review." in item.value for item in app.markdown))

    def test_review_survives_reruns_and_is_hidden_for_changed_snapshot(self):
        app = AppTest.from_string(REVIEW_APP).run()
        self.assertFalse(app.exception)
        click_label(app, "Generate telemetry review")
        self.assertFalse(app.exception)
        report = app.session_state["diagnostic_report"]["markdown"]
        self.assertTrue(any(item.value == report.strip() for item in app.markdown))
        app.run()
        self.assertTrue(any(item.value == report.strip() for item in app.markdown))
        app.slider[0].set_value(1).run()
        self.assertFalse(app.exception)
        self.assertFalse(any(item.value == report.strip() for item in app.markdown))
        self.assertTrue(any("snapshot or API settings changed" in item.value for item in app.info))

    def test_settings_save_clear_and_navigation_use_persistent_state(self):
        with patch.object(settings, "request_gemini_text") as request:
            app = AppTest.from_string(SETTINGS_APP).run()
            app.radio[0].set_value("settings").run()
            app.text_input[0].set_value("  fake-key  ").run()
            self.assertEqual(app.session_state["gemini_api_key"], "")
            click_label(app, "Save key")
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["gemini_api_key"], "fake-key")
            click_label(app, "Return to Dashboard")
            self.assertFalse(app.exception)
            self.assertEqual(app.radio[0].value, "dashboard")
            app.radio[0].set_value("settings").run()
            self.assertEqual(app.text_input[0].value, "fake-key")
            click_label(app, "Clear key")
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["gemini_api_key"], "")
            self.assertEqual(app.text_input[0].value, "")
        request.assert_not_called()

    def test_manual_connection_failure_does_not_expose_provider_exception(self):
        with patch.object(settings, "GENAI_SDK_AVAILABLE", True), \
                patch.object(settings, "request_gemini_text", side_effect=RuntimeError("fake-key-secret")) as request:
            app = AppTest.from_string(SETTINGS_APP).run()
            app.radio[0].set_value("settings").run()
            app.text_input[0].set_value("fake-key-secret")
            click_label(app, "Save key")
            request.assert_not_called()
            click_label(app, "Test connection")
            request.assert_called_once()
            self.assertFalse(app.exception)
            self.assertTrue(any("Connection test failed" in item.value for item in app.warning))
            self.assertFalse(any("fake-key-secret" in item.value for item in app.warning))


if __name__ == "__main__":
    unittest.main()
