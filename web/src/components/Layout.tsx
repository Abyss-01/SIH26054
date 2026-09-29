import React from "react";
import { useDashboardStore } from "../store";
import MissionPlayBar from "./MissionPlayBar";

export default function Layout({ children }: { children: React.ReactNode }) {
  const { snapshot, playing } = useDashboardStore();

  return (
    <div className="layout">
      <aside className="layout__sidebar">
        <div className="layout__brand">
          <div className="layout__logo" aria-hidden="true">
            <svg viewBox="0 0 32 32" width="32" height="32" fill="none">
              <rect width="32" height="32" rx="6" fill="var(--color-surface)" />
              <path
                d="M8 22 L13 12 L18 22"
                stroke="var(--color-cyan)"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="13" cy="12" r="2" fill="var(--color-cyan)" />
            </svg>
          </div>
          <div className="layout__title-block">
            <h1 className="layout__title">AERIS</h1>
            <p className="layout__subtitle">Engine Telemetry</p>
          </div>
        </div>

        <div className="layout__divider" />

        <div className="layout__sidebar-section">
          <span className="layout__section-label">Mission</span>
          <div className="layout__playback-indicator">
            <span className={`layout__playback-dot ${playing ? "layout__playback-dot--playing" : ""}`} />
            <span className="layout__playback-label">{playing ? "Playing" : "Paused"}</span>
          </div>
        </div>

        {snapshot && (
          <div className="layout__sidebar-section">
            <span className="layout__section-label">Status</span>
            <div className="layout__status-row">
              <span className={`layout__status-badge layout__status-badge--${snapshot.status_label.toLowerCase()}`}>
                {snapshot.status_label}
              </span>
              <span className="layout__status-stage">{snapshot.flight_stage}</span>
            </div>
          </div>
        )}

        <div className="layout__divider" />

        <div className="layout__sidebar-section">
          <span className="layout__section-label">Scenario</span>
          <span className="layout__scenario">
            {snapshot ? snapshot.scenario : "No snapshot"}
          </span>
        </div>

        <div className="layout__divider" />

        <div className="layout__sidebar-section">
          <span className="layout__section-label">Seed</span>
          <span className="layout__scenario">{snapshot ? String(snapshot.seed) : "—"}</span>
        </div>

        <div className="layout__sidebar-section">
          <span className="layout__section-label">Noise</span>
          <span className="layout__scenario">
            {snapshot ? snapshot.noise_level.toFixed(1) : "—"}
          </span>
        </div>

      </aside>

      <main className="layout__main">
        {children}
      </main>
    </div>
  );
}
