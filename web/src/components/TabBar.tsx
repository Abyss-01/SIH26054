import React from "react";
import { useDashboardStore } from "../store";
import TelemetryView from "./TelemetryView";
import AIDiagnosticView from "./AIDiagnosticView";
import TableSummaryView from "./TableSummaryView";
import AnomalyAnalysisView from "./AnomalyAnalysisView";

const TABS = [
  { id: "Telemetry", label: "Telemetry", icon: <LineChartIcon /> },
  { id: "AI Diagnostics", label: "AI Diagnostics", icon: <SparkIcon /> },
  { id: "Table Summary", label: "Table Summary", icon: <TableIcon /> },
  { id: "Anomaly Analysis", label: "Anomaly Analysis", icon: <AnomalyIcon /> },
] as const;

export default function TabBar() {
  const [active, setActive] = React.useState<typeof TABS[number]["id"]>("Telemetry");

  return (
    <div className="tab-bar">
      <div className="tab-bar__tabs" role="tablist">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={active === tab.id}
            className={`tab-bar__tab ${active === tab.id ? "tab-bar__tab--active" : ""}`}
            onClick={() => setActive(tab.id)}
          >
            <span className="tab-bar__icon" aria-hidden="true">{tab.icon}</span>
            <span className="tab-bar__label">{tab.label}</span>
          </button>
        ))}
      </div>

      <div className="tab-bar__panel" role="tabpanel">
        {active === "Telemetry" && <TelemetryView />}
        {active === "AI Diagnostics" && <AIDiagnosticView />}
        {active === "Table Summary" && <TableSummaryView />}
        {active === "Anomaly Analysis" && <AnomalyAnalysisView />}
      </div>
    </div>
  );
}

function LineChartIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M3 3v18h18M7 16l4-8 4 4 4-6" />
    </svg>
  );
}

function SparkIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
}

function TableIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 9h18M3 15h18M9 3v18M15 3v18" />
    </svg>
  );
}

function AnomalyIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M12 20V8M6 12l6-6 6 6" />
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}
