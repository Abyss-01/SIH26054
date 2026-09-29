"""Mission console with a replayable profile and inspectable snapshots."""
from html import escape
import json
import streamlit as st
from Demo.telemetry.generator import generate_telemetry_data
from Demo.config.scenarios import SCENARIO_LABELS
from Demo.components.flight_path import advance_mission, render_flight_path_component
from Demo.components.metrics import render_top_metric_cards
from Demo.components.charts import render_telemetry_charts
from Demo.clustering.visualizer import render_clustering_visualizer
from Demo.components.statistics_table import render_statistics_table
from Demo.ai_engine.copilot import render_ai_diagnostic_section


def refresh_snapshot():
    st.session_state["sample_seed"] += 1
    st.session_state["mission_playing"] = False


def render_dashboard_view(manual_scenario: str, noise_level: float):
    # A fragment updates the mission without repeatedly rebuilding navigation.
    playback_enabled = st.session_state.get("mission_playing", False)

    @st.fragment(run_every=2.0 if playback_enabled else None)
    def mission_console():
        # Slider and stage callbacks pause the replay. Rebuild the fragment to
        # unregister its timer immediately, including on a fragment-only rerun.
        if playback_enabled != st.session_state.get("mission_playing", False):
            st.rerun()
        if advance_mission():
            st.rerun()
        st.markdown('<div class="mission-heading"><div><h1>Every signal tells a story.</h1><p>Explore engine health across a mission. Inject a fault. Follow the evidence.</p></div><div class="mission-code"><span>DIGITAL TWIN DEMONSTRATOR</span>ROTAX 915 iS / UAV–01</div></div>', unsafe_allow_html=True)
        flight_dist, flight_stage, selected_scenario = render_flight_path_component(manual_scenario)
        telemetry = generate_telemetry_data(selected_scenario, noise_level, flight_stage, seed=st.session_state["sample_seed"])
        df = telemetry["df"]
        baseline = telemetry["baseline_df"]
        render_top_metric_cards(telemetry)
        st.markdown(f'<div class="snapshot-note"><strong>{escape(SCENARIO_LABELS[selected_scenario])}</strong> · {escape(telemetry["status_desc"])}</div>', unsafe_allow_html=True)
        telemetry_tab, diagnostics_tab, summary_tab, analysis_tab = st.tabs(
            ["Telemetry", "AI Diagnostics", "Table Summary", "Anomaly Analysis"]
        )
        with telemetry_tab:
            render_telemetry_charts(df, selected_scenario, baseline_df=baseline, show_baseline=st.session_state["show_baseline"])
            if st.session_state.get("show_table_summary", False):
                st.divider()
                render_statistics_table(df, baseline_df=baseline, key="telemetry_table_summary")
        with diagnostics_tab:
            render_ai_diagnostic_section(selected_scenario, df, telemetry["health"], telemetry["rul"], telemetry["cluster_text"], flight_stage)
        with summary_tab:
            summary = render_statistics_table(df, baseline_df=baseline)
            st.download_button("Download table summary", summary.to_csv(index=False).encode("utf-8"), file_name=f"aeris-sensor-summary-{st.session_state['sample_seed']}.csv", mime="text/csv", key="download_table_summary")
            with st.expander("Raw telemetry · 30 samples"):
                st.dataframe(df, hide_index=True, width="stretch")
        with analysis_tab:
            render_clustering_visualizer(df, telemetry["is_outlier"], selected_scenario, baseline_df=baseline, anomaly_scores=telemetry["anomaly_scores"], outlier_mask=telemetry["outlier_mask"])
        st.divider()
        info, refresh, export, metadata = st.columns([2.6, 1, 1, 1])
        with info:
            st.caption(f"SNAPSHOT {st.session_state['sample_seed']:04d} · 30 samples · 1 Hz · {flight_dist} km")
        with refresh:
            st.button("New snapshot", on_click=refresh_snapshot, width="stretch", help="Generate a new reproducible noise sample for this scenario.")
        export_df = df.copy()
        export_df.insert(0, "Scenario", selected_scenario)
        export_df.insert(1, "Flight stage", flight_stage)
        export_df.insert(2, "Mission distance (km)", flight_dist)
        export_df.insert(3, "Seed", st.session_state["sample_seed"])
        export_df["Anomaly score"] = telemetry["anomaly_scores"]
        export_df["Flagged"] = telemetry["outlier_mask"]
        with export:
            st.download_button("Export CSV", export_df.to_csv(index=False).encode("utf-8"), file_name=f"aeris-snapshot-{st.session_state['sample_seed']}.csv", mime="text/csv", width="stretch")
        with metadata:
            snapshot = {"data_source": "synthetic demonstration", "scenario": selected_scenario, "flight_stage": flight_stage, "distance_km": flight_dist, "noise_level": noise_level, "seed": st.session_state["sample_seed"], "health_score": telemetry["health"], "status": telemetry["status_label"], "flagged_samples": int(telemetry["outlier_mask"].sum()), "samples": len(df)}
            st.download_button("Snapshot JSON", json.dumps(snapshot, indent=2), file_name=f"aeris-snapshot-{st.session_state['sample_seed']}.json", mime="application/json", width="stretch")
    mission_console()
