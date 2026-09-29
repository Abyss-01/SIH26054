import Plot from "react-plotly.js";
import { useEffect, useMemo, useState } from "react";
import { useDashboardStore } from "../store";

export default function TelemetryView() {
  return <div className="tab-panel"><TelemetryChart /><MetricCards /><FlightPathStrip /><AnomalySummary /></div>;
}

function TelemetryChart() {
  const { snapshot } = useDashboardStore();
  const [chartReady, setChartReady] = useState(false);

  useEffect(() => {
    setChartReady(false);
  }, [snapshot]);
  const data = useMemo<any[]>(() => {
    if (!snapshot) return [];
    const s = snapshot.samples;
    const t = s.map((r) => r["Time (s)"]);
    const rpm = s.map((r) => r["Engine RPM"]);
    const oil = s.map((r) => r["Oil Pressure (bar)"]);
    const egt1 = s.map((r) => r["EGT Cyl 1 (°C)"]);
    const egt2 = s.map((r) => r["EGT Cyl 2 (°C)"]);
    const egt3 = s.map((r) => r["EGT Cyl 3 (°C)"]);
    const egt4 = s.map((r) => r["EGT Cyl 4 (°C)"]);
    const spread = s.map((r) => r["EGT Spread (°C)"]);
    return [
      // Panel 1: Engine RPM
      {
        x: t,
        y: rpm,
        type: "scatter",
        mode: "lines",
        name: "Engine RPM",
        yaxis: "y",
        line: { color: "#22d3ee", width: 2 },
      },
      // Panel 1: Oil Pressure (secondary axis)
      {
        x: t,
        y: oil,
        type: "scatter",
        mode: "lines",
        name: "Oil Pressure (bar)",
        yaxis: "y2",
        line: { color: "#f59e0b", width: 2 },
      },
      // Panel 2: EGT per cylinder
      {
        x: t,
        y: egt1,
        type: "scatter",
        mode: "lines",
        name: "EGT Cyl 1",
        yaxis: "y3",
        line: { color: "#ef4444", width: 1.5 },
      },
      {
        x: t,
        y: egt2,
        type: "scatter",
        mode: "lines",
        name: "EGT Cyl 2",
        yaxis: "y3",
        line: { color: "#f97316", width: 1.5 },
      },
      {
        x: t,
        y: egt3,
        type: "scatter",
        mode: "lines",
        name: "EGT Cyl 3",
        yaxis: "y3",
        line: { color: "#eab308", width: 1.5 },
      },
      {
        x: t,
        y: egt4,
        type: "scatter",
        mode: "lines",
        name: "EGT Cyl 4",
        yaxis: "y3",
        line: { color: "#22c55e", width: 1.5 },
      },
      // Panel 3: EGT Spread
      {
        x: t,
        y: spread,
        type: "scatter",
        mode: "lines+markers",
        name: "EGT Spread",
        yaxis: "y4",
        line: { color: "#a855f7", width: 2 },
        marker: {
          color: snapshot.outlier_mask.map((o) => (o ? "#ef4444" : "#a855f7")),
          size: 6,
        },
      },
      // Panel 4: Flight path (placeholder — fill with stage data when available)
      {
        x: t,
        y: t.map(() => 0),
        type: "scatter",
        mode: "lines",
        name: "Flight Path",
        yaxis: "y5",
        line: { color: "#64748b", width: 1, dash: "dot" },
        showlegend: false,
      },
    ];
  }, [snapshot]);

  const layout = useMemo(
    () => ({
      grid: { rows: 4, columns: 1, pattern: "independent" },
      height: 560,
      margin: { l: 56, r: 56, t: 16, b: 36 },
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: "#94a3b8", family: "system-ui, sans-serif", size: 11 },
      hovermode: "x unified",
      dragmode: "pan",
      xaxis: {
        title: { text: "Time (s)", font: { color: "#94a3b8" } },
        gridcolor: "rgba(148,163,184,0.1)",
        zerolinecolor: "rgba(148,163,184,0.2)",
        ticks: { color: "#64748b" },
      },
      yaxis: {
        title: { text: "Engine RPM", font: { color: "#22d3ee" } },
        gridcolor: "rgba(148,163,184,0.1)",
        zerolinecolor: "rgba(148,163,184,0.2)",
        ticks: { color: "#64748b" },
      },
      yaxis2: {
        title: { text: "Oil Pressure (bar)", font: { color: "#f59e0b" } },
        overlaying: "y",
        side: "right",
        gridcolor: "rgba(0,0,0,0)",
        ticks: { color: "#64748b" },
      },
      yaxis3: {
        title: { text: "EGT (°C)", font: { color: "#94a3b8" } },
        gridcolor: "rgba(148,163,184,0.1)",
        zerolinecolor: "rgba(148,163,184,0.2)",
        ticks: { color: "#64748b" },
      },
      yaxis4: {
        title: { text: "EGT Spread (°C)", font: { color: "#a855f7" } },
        gridcolor: "rgba(148,163,184,0.1)",
        zerolinecolor: "rgba(148,163,184,0.2)",
        ticks: { color: "#64748b" },
      },
      yaxis5: {
        title: { text: "Flight Path", font: { color: "#64748b" } },
        gridcolor: "rgba(148,163,184,0.1)",
        ticks: { color: "#64748b" },
      },
      legend: {
        orientation: "h",
        y: 1.08,
        x: 0,
        font: { color: "#94a3b8", size: 10 },
        bgcolor: "rgba(0,0,0,0)",
      },
      modebar: {
        orientation: "h",
        bgcolor: "rgba(15,23,42,0.85)",
        color: "#64748b",
        activecolor: "#22d3ee",
        activelen: 8,
      },
    }),
    [],
  );

  if (!snapshot) return <TelemetryChartSkeleton />;

  return (
    <div className={`telemetry-chart ${chartReady ? "telemetry-chart--ready" : ""}`} aria-busy={!chartReady}>
      {!chartReady && <div className="telemetry-chart__loading"><span className="telemetry-chart__pulse" />Preparing telemetry workspace</div>}
      <Plot
        data={data}
        layout={layout}
        config={{
          responsive: true,
          displayModeBar: true,
          displaylogo: false,
          modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d", "resetScale2d"],
          scrollZoom: true,
        }}
        useResizeHandler
        onInitialized={() => setChartReady(true)}
        onUpdate={() => setChartReady(true)}
        style={{ width: "100%", height: "100%" }}
      />
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

// ---- Metric cards ----
// Mirrors the Streamlit dashboard: Health Score, Status, Outliers, Severity,
// Dominant Channel, Peak EGT Spread.

function MetricCards() {
  const { snapshot } = useDashboardStore();
  if (!snapshot) return <MetricCardsSkeleton />;

  const cards = [
    {
      label: "Health Score",
      value: snapshot.health.toFixed(1),
      delta: { label: "vs nominal", value: snapshot.health.toFixed(1), positive: snapshot.health >= 100 },
    },
    {
      label: "Status",
      value: snapshot.status_label,
      status: snapshot.status_label.toLowerCase(),
    },
    {
      label: "Outliers",
      value: `${snapshot.outlier_count} (${(snapshot.outlier_fraction * 100).toFixed(0)}%)`,
      delta: snapshot.is_outlier
        ? { label: "Flagged", value: "Yes", positive: false }
        : { label: "Flagged", value: "No", positive: true },
    },
    {
      label: "Severity",
      value: snapshot.severity_score.toFixed(2),
    },
    {
      label: "Dominant Channel",
      value: snapshot.dominant_channel,
    },
    {
      label: "Peak EGT Spread",
      value: `${snapshot.peak_egt_spread.toFixed(1)} °C`,
    },
  ];

  return (
    <div className="metric-cards">
      {cards.map((card) => (
        <MetricCard key={card.label} {...card} />
      ))}
    </div>
  );
}

function MetricCard({
  label,
  value,
  delta,
  status,
}: {
  label: string;
  value: string | number;
  delta?: { label: string; value: string | number; positive: boolean } | null;
  status?: string;
}) {
  return (
    <div className={`metric-card metric-card--${status || ""}`}>
      <div className="metric-card__label">{label}</div>
      <div className="metric-card__value">{value}</div>
      {delta && (
        <div className={`metric-card__delta ${!delta.positive ? "metric-card__delta--negative" : ""}`}>
          <span className="metric-card__delta-label">{delta.label}</span>
          <span className="metric-card__delta-value">{delta.value}</span>
        </div>
      )}
    </div>
  );
}

function MetricCardsSkeleton() {
  return (
    <div className="metric-cards metric-cards--skeleton">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className="metric-card metric-card--skeleton">
          <div className="metric-card__label" />
          <div className="metric-card__value" />
        </div>
      ))}
    </div>
  );
}

// ---- Flight path strip ----
// Shows mission progress along the 300 km profile with stage markers.

const STAGES = [
  { name: "Pre-flight", start: 0, end: 5, color: "#64748b" },
  { name: "Takeoff", start: 5, end: 15, color: "#f59e0b" },
  { name: "Climb", start: 15, end: 45, color: "#3b82f6" },
  { name: "Cruise", start: 45, end: 240, color: "#22d3ee" },
  { name: "Loiter", start: 240, end: 260, color: "#a855f7" },
  { name: "Descent", start: 260, end: 290, color: "#f97316" },
  { name: "Landing", start: 290, end: 300, color: "#22c55e" },
];

function FlightPathStrip() {
  const { snapshot, params } = useDashboardStore();
  const dist = params.flight_distance;

  const stage = useMemo(() => {
    return STAGES.find((s) => dist >= s.start && dist < s.end) ?? STAGES[STAGES.length - 1];
  }, [dist]);

  const progress = Math.min(100, (dist / 300) * 100);

  return (
    <div className="flight-path-strip">
      <div className="flight-path-strip__track">
        {STAGES.map((s) => (
          <div
            key={s.name}
            className="flight-path-strip__segment"
            style={{
              left: `${(s.start / 300) * 100}%`,
              width: `${((s.end - s.start) / 300) * 100}%`,
              backgroundColor: s.color,
            }}
            title={`${s.name}: ${s.start}–${s.end} km`}
          />
        ))}
        <div
          className="flight-path-strip__progress"
          style={{ width: `${progress}%` }}
        />
        <div
          className="flight-path-strip__marker"
          style={{ left: `${progress}%` }}
        />
      </div>
      <div className="flight-path-strip__labels">
        {STAGES.map((s) => (
          <span
            key={s.name}
            className={`flight-path-strip__label ${stage.name === s.name ? "flight-path-strip__label--active" : ""}`}
          >
            {s.name}
          </span>
        ))}
      </div>
      <div className="flight-path-strip__distance">
        <span className="flight-path-strip__distance-value">{dist.toFixed(1)} km</span>
        <span className="flight-path-strip__distance-total">/ 300 km</span>
      </div>
    </div>
  );
}

// ---- Anomaly summary ----
// Shows the cluster assessment and key anomaly metrics.

function AnomalySummary() {
  const { snapshot } = useDashboardStore();
  if (!snapshot) return <AnomalySummarySkeleton />;

  return (
    <div className="anomaly-summary">
      <div className="anomaly-summary__cluster">
        <span className="anomaly-summary__cluster-label">Cluster</span>
        <span className="anomaly-summary__cluster-value">{snapshot.cluster_text}</span>
        {snapshot.cluster_sub && (
          <span className="anomaly-summary__cluster-sub">{snapshot.cluster_sub}</span>
        )}
      </div>
      <div className="anomaly-summary__metrics">
        <div className="anomaly-summary__metric">
          <span className="anomaly-summary__metric-label">Outliers</span>
          <span className="anomaly-summary__metric-value">{snapshot.outlier_count} / {snapshot.samples.length}</span>
        </div>
        <div className="anomaly-summary__metric">
          <span className="anomaly-summary__metric-label">Outlier fraction</span>
          <span className="anomaly-summary__metric-value">{(snapshot.outlier_fraction * 100).toFixed(1)}%</span>
        </div>
        <div className="anomaly-summary__metric">
          <span className="anomaly-summary__metric-label">Severity</span>
          <span className="anomaly-summary__metric-value">{snapshot.severity_score.toFixed(2)}</span>
        </div>
        <div className="anomaly-summary__metric">
          <span className="anomaly-summary__metric-label">Dominant channel</span>
          <span className="anomaly-summary__metric-value">{snapshot.dominant_channel}</span>
        </div>
        <div className="anomaly-summary__metric">
          <span className="anomaly-summary__metric-label">Peak EGT spread</span>
          <span className="anomaly-summary__metric-value">{snapshot.peak_egt_spread.toFixed(1)} °C</span>
        </div>
      </div>
    </div>
  );
}

function AnomalySummarySkeleton() {
  return (
    <div className="anomaly-summary anomaly-summary--skeleton">
      <div className="anomaly-summary__cluster">
        <div className="skeleton skeleton--text" />
        <div className="skeleton skeleton--text skeleton--wide" />
      </div>
      <div className="anomaly-summary__metrics">
        {Array.from({ length: 5 }, (_, i) => (
          <div key={i} className="anomaly-summary__metric">
            <div className="skeleton skeleton--small" />
            <div className="skeleton skeleton--small" />
          </div>
        ))}
      </div>
    </div>
  );
}
