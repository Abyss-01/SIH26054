"""Evidence-led reviews of synthetic telemetry, with optional Gemini narration."""

from datetime import datetime, timezone
import hashlib
import inspect
import json

import numpy as np
import pandas as pd
import streamlit as st
from ai_engine.errors import describe_gemini_error, error_heading

try:
    from google import genai
except ImportError:
    genai = None

GENAI_SDK_AVAILABLE = genai is not None
GEMINI_MODEL = "gemini-3.8-flash"
API_TIMEOUT_MS = 15_000

# Units and precision belong to the measured channels, not aircraft limits.
CHANNELS = {
    "Engine RPM": ("RPM", 0),
    "EGT Cyl 2 (°C)": ("°C", 1),
    "EGT Avg (°C)": ("°C", 1),
    "EGT Spread (°C)": ("°C", 1),
    "CHT (°C)": ("°C", 1),
    "MAP (inHg)": ("inHg", 2),
    "Fuel Pressure (bar)": ("bar", 2),
    "Oil Pressure (bar)": ("bar", 2),
    "Vibration (G)": ("G", 2),
}


def get_gemini_model() -> str:
    """Use the same session-selected model for tests, reviews and provenance."""
    return st.session_state.get("gemini_model", GEMINI_MODEL).strip().removeprefix("models/") or GEMINI_MODEL


def api_configuration_id(api_key: str) -> str:
    """Opaque identity for invalidating reports and connection checks after edits."""
    value = f"{get_gemini_model()}:{GENAI_SDK_AVAILABLE}:{api_key.strip()}"
    return hashlib.sha256(value.encode()).hexdigest()


def snapshot_fingerprint(scenario_name, df_data, health_val, rul_val,
                         cluster_status_text, current_stage, api_key="") -> str:
    """Include every review input and provider configuration in snapshot identity."""
    digest = hashlib.sha256()
    metadata = [scenario_name, float(health_val), rul_val, cluster_status_text,
                current_stage, api_configuration_id(api_key), list(df_data.columns),
                [str(dtype) for dtype in df_data.dtypes]]
    digest.update(json.dumps(metadata, default=str, sort_keys=True).encode())
    digest.update(pd.util.hash_pandas_object(df_data, index=True).values.tobytes())
    return digest.hexdigest()


def summarize_telemetry(df_data: pd.DataFrame) -> dict:
    """Measure finite values; a trend is the last valid value minus the first."""
    data = df_data.copy()
    cylinders = [f"EGT Cyl {number} (°C)" for number in range(1, 5)]
    if all(column in data for column in cylinders):
        cylinder_data = data[cylinders].apply(pd.to_numeric, errors="coerce")
        data["EGT Spread (°C)"] = (
            cylinder_data.max(axis=1) - cylinder_data.min(axis=1)
        ).where(cylinder_data.notna().all(axis=1))
    summary = {}
    for column, (unit, precision) in CHANNELS.items():
        if column not in data:
            continue
        values = pd.to_numeric(data[column], errors="coerce")
        values = values[np.isfinite(values)]
        if values.empty:
            continue
        summary[column] = {
            "min": float(values.min()), "max": float(values.max()),
            "mean": float(values.mean()), "first": float(values.iloc[0]),
            "last": float(values.iloc[-1]),
            "change": float(values.iloc[-1] - values.iloc[0]),
            "samples": len(values), "unit": unit, "precision": precision,
        }
    return summary


def _evidence_markdown(summary: dict) -> str:
    rows = ["| Channel | Minimum | Mean | Maximum | First → last change |",
            "| :--- | ---: | ---: | ---: | ---: |"]
    for column, values in summary.items():
        precision = values["precision"]
        rows.append(
            f"| {column} | {values['min']:.{precision}f} | "
            f"{values['mean']:.{precision}f} | {values['max']:.{precision}f} | "
            f"{values['change']:+.{precision}f} |"
        )
    return "\n".join(rows)


def _local_hypothesis(scenario_name: str, summary: dict) -> str:
    """Explain the selected simulation, without inferring a physical root cause."""
    scenarios = {
        "1.": ("Fuel Pressure (bar)", "fuel pressure instability",
               "Compare fuel pressure with the EGT channels and the nominal overlay."),
        "2.": ("CHT (°C)", "a rising thermal signal",
               "Compare the temperature trend with the same flight stage's nominal overlay."),
        "3.": ("CHT (°C)", "a falling temperature sensor signal",
               "Compare temperature against the nominal overlay. This signal alone cannot distinguish sensor drift from real cooling."),
        "4.": ("Vibration (G)", "an increasing vibration index",
               "Inspect the index trend. These 1 Hz samples cannot resolve high-frequency gearbox vibration or establish gear wear."),
        "5.": ("EGT Spread (°C)", "cylinder temperature divergence",
               "Compare cylinder 2 with all four EGT traces. A temperature split does not establish an injector or ignition fault."),
        "6.": ("Oil Pressure (bar)", "a falling lubrication pressure signal",
               "Compare oil pressure with temperature and vibration to inspect the injected cross-channel pattern."),
        "7.": ("MAP (inHg)", "a falling manifold pressure signal",
               "Compare MAP with engine RPM to inspect the injected boost-loss pattern."),
    }
    selected = next((value for prefix, value in scenarios.items()
                     if scenario_name.startswith(prefix)), None)
    if selected is None:
        if scenario_name != "Nominal Operation (No Anomaly)":
            return ("No scenario-specific interpretation is configured for this label. "
                    "Use the measured table and the matching nominal overlay to review the window.")
        return (
            "The selected scenario contains no injected fault. The table describes the "
            "observed window; the dashboard's reference bands determine whether noisy "
            "samples are flagged. Compare the same flight stage before and after an injection."
        )
    channel, description, next_step = selected
    values = summary.get(channel)
    observation = ""
    if values:
        precision, unit = values["precision"], values["unit"]
        observation = (
            f" **{channel}** changes from **{values['first']:.{precision}f}** to "
            f"**{values['last']:.{precision}f} {unit}**; the measured range is "
            f"**{values['min']:.{precision}f}–{values['max']:.{precision}f} {unit}**."
        )
    return (f"The selected injection models {description}.{observation}\n\n"
            f"{next_step}")


def _window_description(df_data: pd.DataFrame) -> str:
    description = f"{len(df_data)} samples"
    if "Time (s)" in df_data:
        times = pd.to_numeric(df_data["Time (s)"], errors="coerce")
        times = times[np.isfinite(times)]
        if not times.empty:
            description += f" · t = {times.iloc[0]:g}–{times.iloc[-1]:g} s"
    return description


def create_gemini_client(api_key: str):
    """Use a bounded request timeout when supported by the installed optional SDK."""
    if not GENAI_SDK_AVAILABLE:
        raise RuntimeError("Optional Gemini SDK is unavailable")
    arguments = {"api_key": api_key.strip()}
    if "http_options" in inspect.signature(genai.Client).parameters:
        arguments["http_options"] = {"timeout": API_TIMEOUT_MS}
    return genai.Client(**arguments)


def request_gemini_text(api_key: str, prompt: str) -> str:
    client = create_gemini_client(api_key)
    try:
        response = client.models.generate_content(model=get_gemini_model(), contents=prompt)
        result = getattr(response, "text", None)
        if not isinstance(result, str) or not result.strip():
            raise ValueError("Provider returned no text")
        return result.strip()
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


def list_gemini_models(api_key: str) -> list[str]:
    """Discover generation-capable Gemini models only on an explicit UI action."""
    client = create_gemini_client(api_key)
    try:
        names = set()
        for model in client.models.list():
            name = (model.name or "").removeprefix("models/")
            if name.startswith("gemini-") and "generateContent" in (model.supported_actions or []):
                names.add(name)
        return sorted(names, key=lambda name: (name != GEMINI_MODEL, name))
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


def generate_ai_diagnosis(scenario_name: str, df_data: pd.DataFrame,
                          health_val: float, rul_val: float | None,
                          cluster_status_text: str, current_stage: str) -> tuple[str, bool]:
    """Return a measured report and whether Gemini contributed its interpretation."""
    summary = summarize_telemetry(df_data)
    if not summary:
        return "No finite telemetry samples are available for this snapshot.", False
    evidence = _evidence_markdown(summary)
    context = (
        f"**Scenario:** {scenario_name}  \n"
        f"**Flight stage:** {current_stage}  \n"
        f"**Window:** {_window_description(df_data)}  \n"
        f"**Demo fit score:** {health_val:.1f}/100 · {cluster_status_text}"
    )
    interpretation = _local_hypothesis(scenario_name, summary)
    is_live = False
    active_key = st.session_state.get("gemini_api_key", "").strip()
    if active_key and GENAI_SDK_AVAILABLE:
        prompt = (
            "You are explaining a synthetic UAV engine telemetry demonstration. "
            "The scenario is an injected pattern, not independent evidence of a mechanical fault. "
            "Write at most 180 words with two short sections: 'Pattern interpretation' and "
            "'What to compare in the demo'. Ground every numerical claim in the measured table. "
            "Clearly separate observations from hypotheses. Do not invent manufacturer limits, "
            "manual references, maintenance intervals, remaining useful life, a validated physics "
            "model, or confirmed component root causes. Do not recommend flight operations, "
            "maintenance actions, replacements, or certify safety. These 1 Hz samples cannot "
            "resolve high-frequency vibration. Reference bands and fit scores are demo heuristics. "
            f"\n\n{context}\n\n{evidence}"
        )
        try:
            interpretation = request_gemini_text(active_key, prompt)
            is_live = True
        except Exception as error:
            st.session_state["gemini_connection_status"] = {
                "configuration": api_configuration_id(active_key), "ok": False,
                "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                "error": describe_gemini_error(error),
            }
    source = f"Gemini · {get_gemini_model()}" if is_live else "Local evidence summary"
    report = (
        f"# Telemetry review\n\n{context}\n\n"
        f"**Analysis source:** {source}  \n"
        "**Data source:** Synthetic simulation\n\n"
        f"## Measured evidence\n\n{evidence}\n\n"
        "Changes compare the first and last finite samples; units are shown in channel names. "
        "EGT spread is the simultaneous maximum minus minimum across all four cylinders.\n\n"
        f"## {'Gemini interpretation' if is_live else 'Demo interpretation'}\n\n{interpretation}\n\n"
        "_This review describes a synthetic scenario. The fit score and reference bands are "
        "illustrative; component condition and remaining useful life are not established._"
    )
    return report, is_live


def render_ai_diagnostic_section(selected_scenario: str, df: pd.DataFrame,
                                 health: float, rul: float | None,
                                 cluster_text: str, flight_stage: str):
    """Keep a report visible only while its data and API configuration still match."""
    st.markdown("""
        <div class="ai-copilot-card">
            <div style="color:#40d9e6;font-size:.72rem;letter-spacing:.12em;font-weight:700;">AI DIAGNOSTICS</div>
            <h3 style="color:#e8f0f8;margin:8px 0;">Turn telemetry into a clear review</h3>
            <p style="color:#91a4ba;margin:0;">Inspect measured ranges and trends, explain the injected pattern, and export the evidence.</p>
        </div>
    """, unsafe_allow_html=True)
    active_key = st.session_state.get("gemini_api_key", "").strip()
    fingerprint = snapshot_fingerprint(
        selected_scenario, df, health, rul, cluster_text, flight_stage, active_key
    )
    if active_key and GENAI_SDK_AVAILABLE:
        st.caption("Gemini configured · Running a review sends this synthetic telemetry summary to Google.")
    elif active_key:
        st.caption("Key configured · Gemini SDK unavailable; local analysis is ready.")
    else:
        st.caption("Local analysis ready · Add a Gemini key in Settings for optional AI interpretation.")

    if st.button("Generate telemetry review", type="primary", width="stretch",
                 key="run_diagnostic_review"):
        was_playing = st.session_state.get("mission_playing", False)
        st.session_state["mission_playing"] = False
        with st.spinner("Reviewing this telemetry snapshot…"):
            report, is_live = generate_ai_diagnosis(
                selected_scenario, df, health, rul, cluster_text, flight_stage
            )
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        report += f"\n\n---\nGenerated {created_at} · Snapshot `{fingerprint[:8]}`\n"
        st.session_state["diagnostic_report"] = {
            "fingerprint": fingerprint, "markdown": report, "is_live": is_live,
            "created_at": created_at,
            "api_failed": bool(active_key and GENAI_SDK_AVAILABLE and not is_live),
            "error": st.session_state.get("gemini_connection_status", {}).get("error") if not is_live else None,
        }
        if is_live:
            st.session_state["gemini_connection_status"] = {
                "configuration": api_configuration_id(active_key), "ok": True,
                "checked_at": st.session_state["diagnostic_report"]["created_at"],
            }
        if was_playing:
            st.rerun()

    saved_report = st.session_state.get("diagnostic_report")
    if not saved_report:
        return
    if saved_report["fingerprint"] != fingerprint:
        st.info("The snapshot or API settings changed. Generate a new review for the current data.")
        return
    if saved_report["api_failed"]:
        st.warning("Gemini did not return a review. Your local evidence summary is ready; check the saved key and connection in Settings.")
        if saved_report.get("error"):
            st.error(error_heading(saved_report["error"]))
            st.caption(saved_report["error"]["action"])
    source = "Gemini interpretation" if saved_report["is_live"] else "Local evidence summary"
    st.caption(f"{source} · {saved_report['created_at']} · Snapshot {fingerprint[:8]}")
    st.markdown(saved_report["markdown"])
    st.download_button(
        "Download review · Markdown", data=saved_report["markdown"],
        file_name=f"telemetry-review-{fingerprint[:8]}.md", mime="text/markdown",
        key="download_diagnostic_review", width="stretch",
    )
