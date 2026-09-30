import Plot from "react-plotly.js";
import { useEffect, useMemo, useState } from "react";
import { useDashboardStore } from "../store";
import MissionPlayBar from "./MissionPlayBar";
import { cleanFlightStage, cleanScenarioName } from "../utils/formatters";

type SubsystemMode = "stacked" | "powertrain" | "egt" | "spread";

export default function TelemetryView() {
  const { snapshot } = useDashboardStore();

  return (
    <div className="tab-panel telemetry-view">
      {/* 1. Primary Aeronautical KPI Cards */}
      <MetricCards />

      {/* 2. Cluster / Fault Diagnostic Alert Ribbon */}
      {snapshot && <FaultDiagnosticRibbon />}

      {/* 3. Interactive Mission Flight State Controller */}
      <MissionPlayBar />

      {/* 4. Telemetry Timeline with Multi-Subplot Graph */}
      <section className="telemetry-timeline">
        <TelemetryChart />
      </section>
    </div>
  );
}

// ============================================================
// Telemetry Chart with Multi-Panel Subplots & Subsystem Focus
// ============================================================

function TelemetryChart() {
  const { snapshot } = useDashboardStore();
  const [chartReady, setChartReady] = useState(false);
  const [mode, setMode] = useState<SubsystemMode>("stacked");

  useEffect(() => {
    setChartReady(false);
  }, [snapshot, mode]);

  const { data, layout } = useMemo(() => {
    if (!snapshot || !snapshot.samples.length) {
      return { data: [], layout: {} };
    }

    const s = snapshot.samples;
    const t = s.map((r) => r["Time (s)"]);
    const rpm = s.map((r) => r["Engine RPM"]);
    const oil = s.map((r) => r["Oil Pressure (bar)"]);
    const egt1 = s.map((r) => r["EGT Cyl 1 (°C)"]);
    const egt2 = s.map((r) => r["EGT Cyl 2 (°C)"]);
    const egt3 = s.map((r) => r["EGT Cyl 3 (°C)"]);
    const egt4 = s.map((r) => r["EGT Cyl 4 (°C)"]);
    const spread = s.map((r) => r["EGT Spread (°C)"]);
    const outliers = snapshot.outlier_mask;

    const baseLayout: any = {
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(10,15,24,0.75)",
      font: { color: "#94a3b8", family: "system-ui, -apple-system, sans-serif", size: 11 },
      hovermode: "x unified",
      hoverlabel: {
        bgcolor: "#0f172a",
        bordercolor: "#334155",
        font: { color: "#f8fafc", size: 11, family: "monospace" },
      },
      legend: {
        orientation: "h",
        y: 1.05,
        x: 0,
        font: { color: "#cbd5e1", size: 11 },
        bgcolor: "rgba(15,23,42,0.8)",
        bordercolor: "rgba(51,65,85,0.6)",
        borderwidth: 1,
      },
      margin: { l: 65, r: 65, t: 30, b: 40 },
    };

    if (mode === "powertrain") {
      return {
        data: [
          {
            x: t,
            y: rpm,
            type: "scatter",
            mode: "lines+markers",
            name: "Engine RPM",
            line: { color: "#06b6d4", width: 2.5 },
            marker: { size: 4, color: "#06b6d4" },
            yaxis: "y",
          },
          {
            x: t,
            y: oil,
            type: "scatter",
            mode: "lines+markers",
            name: "Oil Pressure (bar)",
            line: { color: "#f59e0b", width: 2.5 },
            marker: { size: 4, color: "#f59e0b" },
            yaxis: "y2",
          },
        ],
        layout: {
          ...baseLayout,
          height: 480,
          xaxis: {
            title: { text: "Time Elapsed (seconds @ 1 Hz)", font: { color: "#94a3b8" } },
            gridcolor: "rgba(148,163,184,0.08)",
            zerolinecolor: "rgba(148,163,184,0.15)",
          },
          yaxis: {
            title: { text: "Engine RPM", font: { color: "#06b6d4", size: 12 } },
            gridcolor: "rgba(148,163,184,0.08)",
            tickfont: { color: "#06b6d4" },
          },
          yaxis2: {
            title: { text: "Oil Pressure (bar)", font: { color: "#f59e0b", size: 12 } },
            overlaying: "y",
            side: "right",
            gridcolor: "rgba(0,0,0,0)",
            tickfont: { color: "#f59e0b" },
          },
        },
      };
    }

    if (mode === "egt") {
      return {
        data: [
          { x: t, y: egt1, type: "scatter", mode: "lines+markers", name: "EGT Cyl 1", line: { color: "#38bdf8", width: 2 }, marker: { size: 3 } },
          { x: t, y: egt2, type: "scatter", mode: "lines+markers", name: "EGT Cyl 2", line: { color: "#f43f5e", width: 2.5 }, marker: { size: 3 } },
          { x: t, y: egt3, type: "scatter", mode: "lines+markers", name: "EGT Cyl 3", line: { color: "#fbbf24", width: 2 }, marker: { size: 3 } },
          { x: t, y: egt4, type: "scatter", mode: "lines+markers", name: "EGT Cyl 4", line: { color: "#34d399", width: 2 }, marker: { size: 3 } },
        ],
        layout: {
          ...baseLayout,
          height: 480,
          xaxis: {
            title: { text: "Time Elapsed (seconds @ 1 Hz)", font: { color: "#94a3b8" } },
            gridcolor: "rgba(148,163,184,0.08)",
          },
          yaxis: {
            title: { text: "Exhaust Gas Temp (°C)", font: { color: "#f8fafc", size: 12 } },
            gridcolor: "rgba(148,163,184,0.08)",
          },
        },
      };
    }

    if (mode === "spread") {
      return {
        data: [
          {
            x: t,
            y: spread,
            type: "scatter",
            mode: "lines+markers",
            name: "EGT Spread (°C)",
            line: { color: "#c084fc", width: 2.5 },
            marker: {
              color: outliers.map((o) => (o ? "#ef4444" : "#c084fc")),
              size: outliers.map((o) => (o ? 9 : 5)),
              symbol: outliers.map((o) => (o ? "diamond" : "circle")),
            },
          },
        ],
        layout: {
          ...baseLayout,
          height: 480,
          shapes: [
            {
              type: "line",
              x0: t[0],
              x1: t[t.length - 1],
              y0: 25,
              y1: 25,
              line: { color: "#f59e0b", width: 1.5, dash: "dash" },
            },
            {
              type: "line",
              x0: t[0],
              x1: t[t.length - 1],
              y0: 35,
              y1: 35,
              line: { color: "#ef4444", width: 1.5, dash: "dot" },
            },
          ],
          annotations: [
            { x: t[t.length - 1], y: 25, text: "Caution Limit (25°C)", showarrow: false, font: { color: "#f59e0b", size: 10 }, xanchor: "right", yanchor: "bottom" },
            { x: t[t.length - 1], y: 35, text: "Critical Limit (35°C)", showarrow: false, font: { color: "#ef4444", size: 10 }, xanchor: "right", yanchor: "bottom" },
          ],
          xaxis: {
            title: { text: "Time Elapsed (seconds @ 1 Hz)", font: { color: "#94a3b8" } },
            gridcolor: "rgba(148,163,184,0.08)",
          },
          yaxis: {
            title: { text: "Cylinder EGT Spread (°C)", font: { color: "#c084fc", size: 12 } },
            gridcolor: "rgba(148,163,184,0.08)",
          },
        },
      };
    }

    // ============================================================
    // DEFAULT: Stacked Subsystems (Clean, Non-Overlapping Panels)
    // ============================================================
    const plotData = [
      // Subplot 1 (Top): Powertrain RPM & Oil Pressure
      {
        x: t,
        y: rpm,
        type: "scatter",
        mode: "lines",
        name: "Engine RPM",
        xaxis: "x",
        yaxis: "y",
        line: { color: "#06b6d4", width: 2 },
      },
      {
        x: t,
        y: oil,
        type: "scatter",
        mode: "lines",
        name: "Oil Pressure (bar)",
        xaxis: "x",
        yaxis: "y2",
        line: { color: "#f59e0b", width: 2 },
      },

      // Subplot 2 (Middle): Cylinder Temperatures
      {
        x: t,
        y: egt1,
        type: "scatter",
        mode: "lines",
        name: "EGT Cyl 1",
        xaxis: "x",
        yaxis: "y3",
        line: { color: "#38bdf8", width: 1.5 },
      },
      {
        x: t,
        y: egt2,
        type: "scatter",
        mode: "lines",
        name: "EGT Cyl 2",
        xaxis: "x",
        yaxis: "y3",
        line: { color: "#f43f5e", width: 2 },
      },
      {
        x: t,
        y: egt3,
        type: "scatter",
        mode: "lines",
        name: "EGT Cyl 3",
        xaxis: "x",
        yaxis: "y3",
        line: { color: "#fbbf24", width: 1.5 },
      },
      {
        x: t,
        y: egt4,
        type: "scatter",
        mode: "lines",
        name: "EGT Cyl 4",
        xaxis: "x",
        yaxis: "y3",
        line: { color: "#34d399", width: 1.5 },
      },

      // Subplot 3 (Bottom): Differential & Anomaly Spread
      {
        x: t,
        y: spread,
        type: "scatter",
        mode: "lines+markers",
        name: "EGT Spread (°C)",
        xaxis: "x",
        yaxis: "y4",
        line: { color: "#c084fc", width: 2 },
        marker: {
          color: outliers.map((o) => (o ? "#ef4444" : "#c084fc")),
          size: outliers.map((o) => (o ? 7 : 4)),
          symbol: outliers.map((o) => (o ? "diamond" : "circle")),
        },
      },
    ];

    const plotLayout: any = {
      ...baseLayout,
      height: 600,
      margin: { l: 65, r: 65, t: 36, b: 40 },
      grid: { rows: 3, columns: 1, pattern: "independent" },

      // Shared bottom X-axis
      xaxis: {
        title: { text: "Time Elapsed (seconds @ 1 Hz)", font: { color: "#94a3b8" } },
        gridcolor: "rgba(148,163,184,0.08)",
        zerolinecolor: "rgba(148,163,184,0.15)",
        ticks: "outside",
        tickcolor: "#64748b",
      },

      // Panel 1: Powertrain (domain 0.70 to 1.0)
      yaxis: {
        title: { text: "RPM", font: { color: "#06b6d4" } },
        domain: [0.71, 1.0],
        gridcolor: "rgba(148,163,184,0.08)",
        tickfont: { color: "#06b6d4" },
      },
      yaxis2: {
        title: { text: "Oil (bar)", font: { color: "#f59e0b" } },
        overlaying: "y",
        side: "right",
        gridcolor: "rgba(0,0,0,0)",
        tickfont: { color: "#f59e0b" },
      },

      // Panel 2: EGT Cylinders (domain 0.36 to 0.65)
      yaxis3: {
        title: { text: "EGT (°C)", font: { color: "#94a3b8" } },
        domain: [0.37, 0.66],
        gridcolor: "rgba(148,163,184,0.08)",
        tickfont: { color: "#94a3b8" },
      },

      // Panel 3: EGT Spread & Anomaly (domain 0.0 to 0.30)
      yaxis4: {
        title: { text: "Spread (°C)", font: { color: "#c084fc" } },
        domain: [0.0, 0.31],
        gridcolor: "rgba(148,163,184,0.08)",
        tickfont: { color: "#c084fc" },
      },
    };

    return { data: plotData, layout: plotLayout };
  }, [snapshot, mode]);

  if (!snapshot) return <TelemetryChartSkeleton />;

  return (
    <div className="telemetry-chart-container">
      <div className="telemetry-chart-toolbar">
        <div className="telemetry-chart-toolbar__left">
          <span className="telemetry-chart-toolbar__title">Telemetry Stream</span>
          <span className="telemetry-chart-toolbar__rate">30 Samples · 1 Hz Synchronized</span>
        </div>

        <div className="telemetry-chart-toolbar__modes" role="tablist" aria-label="Chart Subsystem View">
          <button
            type="button"
            className={`telemetry-chart-mode-btn ${mode === "stacked" ? "telemetry-chart-mode-btn--active" : ""}`}
            onClick={() => setMode("stacked")}
          >
            Stacked Subsystems
          </button>
          <button
            type="button"
            className={`telemetry-chart-mode-btn ${mode === "powertrain" ? "telemetry-chart-mode-btn--active" : ""}`}
            onClick={() => setMode("powertrain")}
          >
            Powertrain (RPM & Oil)
          </button>
          <button
            type="button"
            className={`telemetry-chart-mode-btn ${mode === "egt" ? "telemetry-chart-mode-btn--active" : ""}`}
            onClick={() => setMode("egt")}
          >
            Cylinders (EGT 1–4)
          </button>
          <button
            type="button"
            className={`telemetry-chart-mode-btn ${mode === "spread" ? "telemetry-chart-mode-btn--active" : ""}`}
            onClick={() => setMode("spread")}
          >
            Differential & Outliers
          </button>
        </div>
      </div>

      <div className={`telemetry-chart ${chartReady ? "telemetry-chart--ready" : ""}`} aria-busy={!chartReady}>
        {!chartReady && (
          <div className="telemetry-chart__loading">
            <span className="telemetry-chart__pulse" />
            Synchronizing telemetry channels…
          </div>
        )}
        <Plot
          data={data}
          layout={layout}
          config={{
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
            scrollZoom: false,
          }}
          useResizeHandler
          onInitialized={() => setChartReady(true)}
          onUpdate={() => setChartReady(true)}
          style={{ width: "100%", height: "100%" }}
        />
      </div>
    </div>
  );
}

function TelemetryChartSkeleton() {
  return (
    <div className="telemetry-chart telemetry-chart--skeleton">
      <div className="chart-skeleton-chart" />
      <div className="chart-skeleton-legend" />
    </div>
  );
}

// ============================================================
// Primary Aeronautical Metric Cards
// ============================================================

function MetricCards() {
  const { snapshot } = useDashboardStore();
  if (!snapshot) return <MetricCardsSkeleton />;

  const isDegraded = snapshot.health < 80;
  const isCritical = snapshot.status_label === "CRITICAL";

  return (
    <div className="metric-cards">
      {/* 1. Health Index */}
      <div className={`metric-card ${isCritical ? "metric-card--critical" : isDegraded ? "metric-card--warning" : "metric-card--normal"}`}>
        <div className="metric-card__header">
          <span className="metric-card__label">System Health Index</span>
          <span className="metric-card__chip">{snapshot.health >= 90 ? "NOMINAL" : isCritical ? "CRITICAL" : "DEGRADED"}</span>
        </div>
        <div className="metric-card__value-row">
          <span className="metric-card__value">{snapshot.health.toFixed(1)}%</span>
        </div>
        <div className="metric-card__footer">
          <span className={`metric-card__sub-label ${isDegraded ? "text-critical" : "text-success"}`}>
            {snapshot.health >= 98
              ? "Optimal powertrain condition"
              : `${(snapshot.health - 100).toFixed(1)}% vs nominal envelope`}
          </span>
        </div>
      </div>

      {/* 2. Operational Status */}
      <div className={`metric-card ${isCritical ? "metric-card--critical" : isDegraded ? "metric-card--warning" : "metric-card--normal"}`}>
        <div className="metric-card__header">
          <span className="metric-card__label">Operational Status</span>
          <span className={`status-indicator-dot status-indicator-dot--${snapshot.status_label.toLowerCase()}`} />
        </div>
        <div className="metric-card__value-row">
          <span className={`metric-card__value metric-card__status-text status-text--${snapshot.status_label.toLowerCase()}`}>
            {snapshot.status_label}
          </span>
        </div>
        <div className="metric-card__footer">
          <span className="metric-card__sub-label">
            Mission Flight Stage: <strong className="text-highlight">{cleanFlightStage(snapshot.flight_stage)}</strong>
          </span>
        </div>
      </div>

      {/* 3. Outlier Flagging */}
      <div className={`metric-card ${snapshot.outlier_count > 0 ? "metric-card--critical" : "metric-card--normal"}`}>
        <div className="metric-card__header">
          <span className="metric-card__label">Flagged Outliers</span>
          <span className="metric-card__chip">{(snapshot.outlier_fraction * 100).toFixed(0)}% SAMPLES</span>
        </div>
        <div className="metric-card__value-row">
          <span className="metric-card__value">
            {snapshot.outlier_count} <span className="metric-card__denom">/ {snapshot.samples.length}</span>
          </span>
        </div>
        <div className="metric-card__footer">
          <span className={`metric-card__sub-label ${snapshot.outlier_count > 0 ? "text-critical" : "text-muted"}`}>
            {snapshot.outlier_count > 0 ? "Anomalous window threshold triggered" : "Zero sensor deviations"}
          </span>
        </div>
      </div>

      {/* 4. Dominant Deviating Channel */}
      <div className="metric-card">
        <div className="metric-card__header">
          <span className="metric-card__label">Dominant Channel</span>
          <span className="metric-card__chip">SEV {snapshot.severity_score.toFixed(2)}</span>
        </div>
        <div className="metric-card__value-row">
          <span className="metric-card__value metric-card__value--sm">{snapshot.dominant_channel}</span>
        </div>
        <div className="metric-card__footer">
          <span className="metric-card__sub-label">
            Primary driver of telemetry divergence
          </span>
        </div>
      </div>

      {/* 5. Peak EGT Differential */}
      <div className={`metric-card ${snapshot.peak_egt_spread > 25 ? "metric-card--critical" : "metric-card--normal"}`}>
        <div className="metric-card__header">
          <span className="metric-card__label">Peak EGT Spread</span>
          <span className="metric-card__chip">LIMIT 25°C</span>
        </div>
        <div className="metric-card__value-row">
          <span className="metric-card__value">{snapshot.peak_egt_spread.toFixed(1)} °C</span>
        </div>
        <div className="metric-card__footer">
          <span className={`metric-card__sub-label ${snapshot.peak_egt_spread > 25 ? "text-critical" : "text-success"}`}>
            {snapshot.peak_egt_spread > 25 ? "Cylinder imbalance exceeds threshold" : "Thermal balance balanced"}
          </span>
        </div>
      </div>
    </div>
  );
}

function MetricCardsSkeleton() {
  return (
    <div className="metric-cards metric-cards--skeleton">
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="metric-card metric-card--skeleton">
          <div className="skeleton skeleton--text" />
          <div className="skeleton skeleton--wide" />
        </div>
      ))}
    </div>
  );
}

// ============================================================
// Fault Diagnostic Ribbon (Replaces repetitive duplicate metric box)
// ============================================================

function FaultDiagnosticRibbon() {
  const { snapshot } = useDashboardStore();
  if (!snapshot) return null;

  const isCritical = snapshot.status_label === "CRITICAL";
  const isWarning = snapshot.status_label === "WARNING";

  return (
    <div className={`fault-diagnostic-ribbon ${isCritical ? "fault-diagnostic-ribbon--critical" : isWarning ? "fault-diagnostic-ribbon--warning" : "fault-diagnostic-ribbon--normal"}`}>
      <div className="fault-diagnostic-ribbon__icon" aria-hidden="true">
        {isCritical ? <AlertTriangleIcon /> : isWarning ? <AlertCircleIcon /> : <CheckCircleIcon />}
      </div>
      <div className="fault-diagnostic-ribbon__body">
        <div className="fault-diagnostic-ribbon__title-row">
          <span className="fault-diagnostic-ribbon__tag">
            {isCritical ? "FAULT CLUSTER DETECTED" : isWarning ? "ADVISORY" : "SYSTEM STABLE"}
          </span>
          <span className="fault-diagnostic-ribbon__cluster-title">{snapshot.cluster_text}</span>
          {snapshot.is_outlier && (
            <span className="fault-diagnostic-ribbon__timing">Onset at T+15s</span>
          )}
        </div>
        <p className="fault-diagnostic-ribbon__description">
          {snapshot.status_desc}
          {snapshot.cluster_sub ? ` — ${snapshot.cluster_sub}` : ""}
        </p>
      </div>
    </div>
  );
}

function AlertTriangleIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function AlertCircleIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function CheckCircleIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <polyline points="9 11 12 14 22 4" />
    </svg>
  );
}
