import React from "react";
import { useDashboardStore } from "../store";
import { SCENARIOS, type Scenario } from "../types";
import { cleanFlightStage, cleanScenarioName } from "../utils/formatters";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { snapshot, playing, error, params, setParams, fetchSnapshot } = useDashboardStore();

  const selectScenario = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setParams({ scenario: event.target.value as Scenario });
    void fetchSnapshot();
  };

  const setNoise = (event: React.ChangeEvent<HTMLInputElement>) => {
    setParams({ noise_level: Number(event.target.value) });
  };

  const refreshSnapshot = () => {
    setParams({ sample_seed: Math.floor(Math.random() * 10_000) });
    void fetchSnapshot();
  };

  const applyNoise = () => void fetchSnapshot();

  const activeStage = cleanFlightStage(snapshot?.flight_stage ?? "Pre-flight");
  const activeScenario = cleanScenarioName(snapshot?.scenario ?? params.scenario);
  const isCritical = snapshot?.status_label === "CRITICAL";
  const isWarning = snapshot?.status_label === "WARNING";

  return (
    <div className="layout">
      {/* ============================================================
          SIDEBAR CONTROLS & FLIGHT PROFILE
          ============================================================ */}
      <aside className="layout__sidebar">
        {/* Brand */}
        <div className="layout__brand">
          <div className="layout__logo" aria-hidden="true">
            <svg viewBox="0 0 32 32" width="30" height="30" fill="none">
              <rect width="32" height="32" rx="7" fill="#0d1b2a" stroke="#1e293b" />
              <path
                d="M7 21 L16 9 L25 21 L16 17 Z"
                fill="rgba(6,182,212,0.2)"
                stroke="#06b6d4"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="16" cy="9" r="2.5" fill="#38bdf8" />
            </svg>
          </div>
          <div className="layout__title-block">
            <div className="layout__title-row">
              <h1 className="layout__title">AERIS</h1>
              <span className="layout__badge-version">v2.1</span>
            </div>
            <p className="layout__subtitle">UAV Engine Telemetry</p>
          </div>
        </div>

        <div className="layout__divider" />

        {/* Engine Model Specification */}
        <div className="sidebar-engine-spec">
          <span className="sidebar-engine-spec__label">PROPULSION UNIT</span>
          <strong className="sidebar-engine-spec__val">ROTAX 915 iS / UAV–01</strong>
          <span className="sidebar-engine-spec__sub">Turbocharged 4-Cylinder EFI</span>
        </div>

        <div className="layout__divider" />

        {/* Scenario Controls */}
        <div className="layout__sidebar-section layout__controls">
          <label className="layout__section-label" htmlFor="scenario-preset">
            Scenario Preset
          </label>
          <select
            id="scenario-preset"
            className="layout__select"
            value={params.scenario}
            onChange={selectScenario}
          >
            <optgroup label="Nominal Flight Profiles">
              {SCENARIOS.slice(0, 2).map((preset) => (
                <option key={preset.value} value={preset.value}>
                  {preset.label}
                </option>
              ))}
            </optgroup>
            <optgroup label="Simulated Engine Faults">
              {SCENARIOS.slice(2).map((preset) => (
                <option key={preset.value} value={preset.value}>
                  {preset.label}
                </option>
              ))}
            </optgroup>
          </select>
          <p className="layout__control-help">
            Inject realistic sensor anomalies or run nominal flight envelope profiles.
          </p>
        </div>

        {/* Noise Slider */}
        <div className="layout__sidebar-section layout__controls">
          <div className="layout__slider-header">
            <label className="layout__section-label" htmlFor="noise-level">
              Sensor Noise
            </label>
            <span className="layout__slider-val">{params.noise_level.toFixed(1)}σ</span>
          </div>
          <input
            id="noise-level"
            className="layout__range"
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={params.noise_level}
            onChange={setNoise}
            onMouseUp={applyNoise}
            onTouchEnd={applyNoise}
          />
          <div className="layout__range-labels">
            <span>0.0 (Clean)</span>
            <span>1.0 (Nominal)</span>
            <span>2.0 (High Variance)</span>
          </div>
        </div>

        {/* New Snapshot Button */}
        <button type="button" className="layout__new-snapshot" onClick={refreshSnapshot}>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.3" />
          </svg>
          <span>Regenerate Snapshot</span>
        </button>

        <div className="layout__divider" />

        {/* Telemetry Status Summary in Sidebar */}
        <div className="sidebar-status-box">
          <div className="sidebar-status-box__row">
            <span className="layout__section-label">System State</span>
            <span
              className={`layout__status-badge ${
                isCritical
                  ? "layout__status-badge--critical"
                  : isWarning
                  ? "layout__status-badge--warning"
                  : "layout__status-badge--normal"
              }`}
            >
              {snapshot?.status_label ?? "NORMAL"}
            </span>
          </div>

          <div className="sidebar-status-box__row">
            <span className="layout__section-label">Flight Stage</span>
            <strong className="sidebar-status-box__val">{activeStage}</strong>
          </div>

          <div className="sidebar-status-box__row">
            <span className="layout__section-label">Distance</span>
            <strong className="sidebar-status-box__val">
              {params.flight_distance.toFixed(1)} km
            </strong>
          </div>

          <div className="sidebar-status-box__row">
            <span className="layout__section-label">Seed ID</span>
            <span className="sidebar-status-box__code">#{snapshot?.seed ?? params.sample_seed}</span>
          </div>

          <div className="sidebar-status-box__row">
            <span className="layout__section-label">Stream Status</span>
            <span className="sidebar-stream-indicator">
              <span className={`sidebar-stream-dot ${playing ? "sidebar-stream-dot--active" : ""}`} />
              {playing ? "STREAMING" : "STANDBY"}
            </span>
          </div>
        </div>
      </aside>

      {/* ============================================================
          MAIN TELEMETRY CONSOLE
          ============================================================ */}
      <main className="layout__main">
        {error && (
          <div className="demo-notice" role="status">
            {error}
          </div>
        )}

        {/* Professional Aeronautical Command Header */}
        <header className="aerospace-header">
          <div className="aerospace-header__left">
            <div className="aerospace-header__system-tag">
              <span className="aerospace-header__dot" />
              <span>ROTAX 915 iS DIGITAL TWIN CONSOLE</span>
              <span className="aerospace-header__sep">/</span>
              <span className="aerospace-header__uav-id">UAV–01 MISSION DEPLOYMENT</span>
            </div>
            <h2 className="aerospace-header__scenario-title">{activeScenario}</h2>
          </div>

          <div className="aerospace-header__right">
            <div className="aerospace-header__metric-pill">
              <span className="aerospace-header__pill-label">STAGE</span>
              <strong className="aerospace-header__pill-val">{activeStage.toUpperCase()}</strong>
            </div>

            <div className="aerospace-header__metric-pill">
              <span className="aerospace-header__pill-label">DISTANCE</span>
              <strong className="aerospace-header__pill-val">{params.flight_distance.toFixed(1)} km</strong>
            </div>

            <div className="aerospace-header__metric-pill">
              <span className="aerospace-header__pill-label">HEALTH</span>
              <strong
                className={`aerospace-header__pill-val ${
                  isCritical ? "text-critical" : isWarning ? "text-warning" : "text-success"
                }`}
              >
                {snapshot ? `${snapshot.health.toFixed(1)}%` : "—"}
              </strong>
            </div>

            <div className="aerospace-header__stream-badge">
              <span className="stream-badge-dot" />
              <span>1 Hz LIVE</span>
            </div>
          </div>
        </header>

        {children}
      </main>
    </div>
  );
}
