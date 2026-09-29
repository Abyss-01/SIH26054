"""Explicit, session-scoped configuration for optional Gemini interpretation."""

from datetime import datetime, timezone

import streamlit as st

from Demo.ai_engine.copilot import (
    GEMINI_MODEL, GENAI_SDK_AVAILABLE, api_configuration_id, request_gemini_text,
    get_gemini_model, list_gemini_models,
)
from Demo.ai_engine.errors import describe_gemini_error, error_heading


def _return_to_dashboard():
    # Callbacks run before the app's navigation radio is instantiated on rerun.
    st.session_state["active_page"] = "dashboard"


def _save_api_key():
    new_key = st.session_state.get("_gemini_key_input", "").strip()
    if new_key != st.session_state.get("gemini_api_key", ""):
        st.session_state.pop("gemini_connection_status", None)
        st.session_state.pop("gemini_available_models", None)
        st.session_state.pop("gemini_model_list_error", None)
    st.session_state["gemini_api_key"] = new_key
    st.session_state["_gemini_key_input"] = new_key
    st.session_state["_gemini_settings_notice"] = (
        "Key saved for this session. Test the connection when ready."
        if new_key else "Key cleared. Local telemetry reviews are ready."
    )


def _clear_api_key():
    st.session_state["gemini_api_key"] = ""
    st.session_state["_gemini_key_input"] = ""
    st.session_state.pop("gemini_connection_status", None)
    st.session_state.pop("gemini_available_models", None)
    st.session_state.pop("gemini_model_list_error", None)
    st.session_state["_gemini_settings_notice"] = "Key cleared. Local telemetry reviews are ready."


def _model_changed():
    st.session_state["gemini_model"] = get_gemini_model()
    st.session_state.pop("gemini_connection_status", None)


def _use_discovered_model():
    st.session_state["gemini_model"] = st.session_state["_gemini_discovered_model"]
    _model_changed()


def render_settings_view():
    """Only explicit connection tests and model discovery contact the provider."""
    st.markdown("""
        <div class="settings-card">
            <div style="color:#40d9e6;font-size:.72rem;letter-spacing:.12em;font-weight:700;">INTEGRATIONS</div>
            <h2 style="color:#e8f0f8;margin:8px 0;">An optional second perspective</h2>
            <p style="color:#91a4ba;margin:0;">Local telemetry reviews work immediately. Connect Gemini to add an AI interpretation of the same measured evidence.</p>
        </div>
    """, unsafe_allow_html=True)
    st.write("")
    configuration_column, status_column = st.columns([1.7, 1], gap="large")
    with configuration_column:
        st.subheader("Gemini connection")
        st.caption(f"Model · {get_gemini_model()}")
        if "_gemini_key_input" not in st.session_state:
            st.session_state["_gemini_key_input"] = st.session_state.get("gemini_api_key", "")
        with st.form("gemini_settings_form"):
            st.text_input(
                "API key", type="password", key="_gemini_key_input",
                placeholder="Paste your Gemini API key",
                help="Saved in this Streamlit session; the app does not write the key to a file.",
            )
            st.caption("Edits take effect when you save. Connection tests and AI reviews send requests to Google.")
            save_column, clear_column = st.columns(2)
            with save_column:
                st.form_submit_button("Save key", type="primary", on_click=_save_api_key,
                                      width="stretch")
            with clear_column:
                st.form_submit_button("Clear key", on_click=_clear_api_key,
                                      width="stretch")
        notice = st.session_state.pop("_gemini_settings_notice", None)
        if notice:
            st.success(notice)
        active_key = st.session_state.get("gemini_api_key", "").strip()
        st.session_state.setdefault("gemini_model", GEMINI_MODEL)
        st.text_input("Model", key="gemini_model", on_change=_model_changed,
                      help="Used for both connection tests and AI diagnostics. Change this if Google reports that a model is unavailable.")
        if st.button("Load available models", disabled=not active_key or not GENAI_SDK_AVAILABLE):
            with st.spinner("Loading models available through your saved key…"):
                try:
                    st.session_state["gemini_available_models"] = list_gemini_models(active_key)
                    st.session_state.pop("gemini_model_list_error", None)
                except Exception as error:
                    st.session_state.pop("gemini_available_models", None)
                    st.session_state["gemini_model_list_error"] = describe_gemini_error(error)
        discovery_error = st.session_state.get("gemini_model_list_error")
        if discovery_error:
            st.error(f"Model discovery failed · {error_heading(discovery_error)}")
            st.caption(discovery_error["action"])
        available = st.session_state.get("gemini_available_models")
        if available:
            st.selectbox("Available generation models", available, key="_gemini_discovered_model")
            st.button("Use selected model", on_click=_use_discovered_model)
            st.caption("Choose a text model for diagnostics. Model listing alone does not verify generation access or quota; test the selected model next.")
        elif available == []:
            st.warning("Google returned no compatible Gemini generation models for this key.")
        test_column, back_column = st.columns(2)
        with test_column:
            if st.button("Test connection", width="stretch",
                         disabled=not active_key or not GENAI_SDK_AVAILABLE):
                with st.spinner("Testing saved Gemini key…"):
                    error_details = None
                    try:
                        request_gemini_text(active_key, "Reply with exactly: Connection verified.")
                        connected = True
                    except Exception as error:
                        connected = False
                        error_details = describe_gemini_error(error)
                st.session_state["gemini_connection_status"] = {
                    "configuration": api_configuration_id(active_key), "ok": connected,
                    "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                    "error": error_details,
                }
        with back_column:
            st.button("Return to Dashboard", width="stretch",
                      on_click=_return_to_dashboard)

    with status_column:
        st.subheader("Connection status")
        connection = st.session_state.get("gemini_connection_status", {})
        matches = connection.get("configuration") == api_configuration_id(active_key)
        if not active_key:
            st.info("Local analysis ready")
            st.caption("No API key saved. Every demo scenario and local report remains available.")
        elif not GENAI_SDK_AVAILABLE:
            st.warning("Key saved · SDK unavailable")
            st.caption("Install the optional google-genai package to enable Gemini. Local analysis remains available.")
        elif matches and connection.get("ok"):
            st.success("Connection verified")
            st.caption(f"Last successful request · {connection['checked_at']}")
        elif matches:
            st.warning("Connection test failed")
            failure = connection.get("error")
            if failure:
                st.error(error_heading(failure))
                st.write(failure["action"])
                st.caption(f"Model · {get_gemini_model()} · Last attempt · {connection['checked_at']}")
            else:
                st.caption("This earlier test did not record the failure reason. Test the connection again to see an error code and next step.")
            st.caption("Local analysis remains available.")
            st.markdown("[Gemini API troubleshooting](https://ai.google.dev/gemini-api/docs/troubleshooting)")
        else:
            st.info("Key saved · Not tested")
            st.caption("A saved key becomes a verified connection only after a successful request.")
        st.divider()
        st.markdown("**What is shared**")
        st.caption("Generating a Gemini review sends scenario context and aggregate synthetic sensor statistics. The local fallback makes no API request.")
        st.markdown("**Session storage**")
        st.caption("The app keeps the saved key in session memory. Clear it here to return to local analysis. A new session can load GEMINI_API_KEY from the environment.")
