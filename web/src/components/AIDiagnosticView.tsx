import React from "react";
import { useDashboardStore } from "../store";
import { useReviewStore } from "../store";
import { cleanFlightStage, cleanScenarioName } from "../utils/formatters";

interface ChannelStat {
  channel: string;
  min: number;
  mean: number;
  max: number;
  delta: number;
  nominal: string;
  isAnomalous: boolean;
  status: "CRITICAL" | "WARNING" | "NORMAL";
}

export default function AIDiagnosticView() {
  const { snapshot, params } = useDashboardStore();
  const { review, loading, error, setReview, setLoading, setError, clearReview } = useReviewStore();
  const [copied, setCopied] = React.useState(false);

  // Compute structured channel stats
  const channelStats = React.useMemo<ChannelStat[]>(() => {
    if (!snapshot) return [];
    const channels = [
      { name: "Engine RPM", nominal: "5000–5500 RPM" },
      { name: "Oil Pressure (bar)", nominal: "3.5–5.0 bar" },
      { name: "CHT", nominal: "140–180 °C" },
      { name: "MAP", nominal: "30–38 inHg" },
      { name: "EGT Cyl 1 (°C)", nominal: "680–740 °C" },
      { name: "EGT Cyl 2 (°C)", nominal: "680–740 °C" },
      { name: "EGT Cyl 3 (°C)", nominal: "680–740 °C" },
      { name: "EGT Cyl 4 (°C)", nominal: "680–740 °C" },
      { name: "EGT Spread (°C)", nominal: "< 25.0 °C" },
    ];

    return channels.map(({ name, nominal }) => {
      const vals = snapshot.samples
        .map((r) => r[name as keyof typeof r])
        .filter((v): v is number => typeof v === "number" && Number.isFinite(v));

      if (vals.length === 0) {
        return { channel: name, min: 0, mean: 0, max: 0, delta: 0, nominal, isAnomalous: false, status: "NORMAL" };
      }

      const min = Math.min(...vals);
      const max = Math.max(...vals);
      const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
      const delta = vals.length >= 2 ? vals[vals.length - 1] - vals[0] : 0;

      const isDominant = snapshot.dominant_channel.toLowerCase().includes(name.toLowerCase());
      const isSpreadOver = name.includes("Spread") && max > 25;
      const isOilUnder = name.includes("Oil") && min < 3.2;

      let status: "CRITICAL" | "WARNING" | "NORMAL" = "NORMAL";
      if (isDominant || (snapshot.status_label === "CRITICAL" && (isSpreadOver || isOilUnder))) {
        status = "CRITICAL";
      } else if (isSpreadOver || Math.abs(delta) > 15) {
        status = "WARNING";
      }

      return {
        channel: name,
        min,
        mean,
        max,
        delta,
        nominal,
        isAnomalous: status !== "NORMAL",
        status,
      };
    });
  }, [snapshot]);

  const handleGenerate = async () => {
    if (!snapshot) return;
    setLoading(true);
    setError(null);
    try {
      await new Promise((r) => setTimeout(r, 650));
      const markdown = buildComprehensiveMarkdown(snapshot, channelStats);
      setReview({ markdown, live: false });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Diagnostic generation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (!review) return;
    navigator.clipboard.writeText(review.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!review) return;
    const blob = new Blob([review.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aeris-diagnostic-${params.sample_seed}-${params.flight_distance}km.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!snapshot) {
    return (
      <div className="tab-panel">
        <div className="empty-state">
          <p>Initialize a telemetry snapshot to run AI diagnostics.</p>
        </div>
      </div>
    );
  }

  const isCritical = snapshot.status_label === "CRITICAL";
  const isWarning = snapshot.status_label === "WARNING";
  const scenarioClean = cleanScenarioName(snapshot.scenario);
  const stageClean = cleanFlightStage(snapshot.flight_stage);

  return (
    <div className="tab-panel ai-diagnostics-view">
      {/* Header & Controls */}
      <div className="ai-diag-header">
        <div className="ai-diag-header__info">
          <div className="ai-diag-header__eyebrow">
            <span>AEROSPACE DIAGNOSTIC AGENT</span>
            <span className="ai-diag-header__pill">ROTAX 915 iS ENGINE</span>
          </div>
          <h2 className="ai-diag-header__title">AI Telemetry Health Assessment</h2>
          <p className="ai-diag-header__sub">
            Real-time multi-channel anomaly detection, physics-informed fault isolation, and flight crew directives.
          </p>
        </div>

        <div className="ai-diag-header__actions">
          <button
            type="button"
            className="ai-diag-btn ai-diag-btn--primary"
            disabled={loading}
            onClick={handleGenerate}
          >
            {loading ? (
              <>
                <span className="spinner-dot" />
                Analyzing Telemetry…
              </>
            ) : review ? (
              "Regenerate Diagnostic"
            ) : (
              "Run AI Diagnostic"
            )}
          </button>

          {review && (
            <>
              <button
                type="button"
                className="ai-diag-btn ai-diag-btn--secondary"
                onClick={handleCopy}
              >
                {copied ? "Copied!" : "Copy Report"}
              </button>
              <button
                type="button"
                className="ai-diag-btn ai-diag-btn--secondary"
                onClick={handleDownload}
              >
                Export .MD
              </button>
              <button
                type="button"
                className="ai-diag-btn ai-diag-btn--subtle"
                onClick={() => clearReview()}
              >
                Reset
              </button>
            </>
          )}
        </div>
      </div>

      {error && <div className="ai-diag-alert ai-diag-alert--error">{error}</div>}

      {/* Main Diagnostic Panel */}
      {review ? (
        <div className="ai-diag-report">
          {/* Executive Overview Banner */}
          <div className={`ai-diag-banner ${isCritical ? "ai-diag-banner--critical" : isWarning ? "ai-diag-banner--warning" : "ai-diag-banner--normal"}`}>
            <div className="ai-diag-banner__left">
              <span className="ai-diag-banner__tag">
                {isCritical ? "CRITICAL MALFUNCTION CONFIRMED" : isWarning ? "OPERATIONAL CAUTION" : "ALL SYSTEMS NOMINAL"}
              </span>
              <h3 className="ai-diag-banner__heading">{scenarioClean}</h3>
              <p className="ai-diag-banner__meta">
                Flight Stage: <strong>{stageClean}</strong> · Mission Distance: <strong>{snapshot.flight_distance_km.toFixed(1)} km</strong> ·
                Health Index: <strong>{snapshot.health.toFixed(1)}%</strong> · Outlier Rate: <strong>{(snapshot.outlier_fraction * 100).toFixed(0)}%</strong>
              </p>
            </div>
            <div className="ai-diag-banner__right">
              <span className="ai-diag-banner__score-label">Anomaly Severity</span>
              <span className="ai-diag-banner__score-val">{snapshot.severity_score.toFixed(2)}</span>
              <span className="ai-diag-banner__score-sub">Threshold: 2.50</span>
            </div>
          </div>

          <div className="ai-diag-grid">
            {/* Left Column: Root Cause & Analysis */}
            <div className="ai-diag-column">
              <section className="ai-diag-card">
                <div className="ai-diag-card__header">
                  <span className="ai-diag-card__num">01</span>
                  <h4>Root Cause & Physical Mechanism</h4>
                </div>
                <div className="ai-diag-card__body">
                  <p className="ai-diag-prose">{snapshot.status_desc}</p>
                  <p className="ai-diag-prose">
                    <strong>Cluster Assessment:</strong> {snapshot.cluster_text}
                    {snapshot.cluster_sub ? ` — ${snapshot.cluster_sub}` : ""}
                  </p>
                  <div className="ai-diag-highlight-box">
                    <span className="ai-diag-highlight-label">Primary Driver Channel:</span>
                    <strong className="text-highlight">{snapshot.dominant_channel}</strong>
                    <span className="ai-diag-highlight-sub">
                      Peak EGT Spread reached <strong>{snapshot.peak_egt_spread.toFixed(1)} °C</strong> (Caution envelope: 25.0 °C).
                    </span>
                  </div>
                </div>
              </section>

              {/* Operator Action Checklist */}
              <section className="ai-diag-card">
                <div className="ai-diag-card__header">
                  <span className="ai-diag-card__num">02</span>
                  <h4>Flight Crew / UAV Operator Directives</h4>
                </div>
                <div className="ai-diag-card__body">
                  <ul className="ai-diag-checklist">
                    {getActionDirectives(scenarioClean, isCritical).map((step, idx) => (
                      <li key={idx} className="ai-diag-checklist__item">
                        <span className="ai-diag-checklist__badge">{idx + 1}</span>
                        <div className="ai-diag-checklist__content">
                          <strong>{step.title}</strong>
                          <p>{step.detail}</p>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </section>
            </div>

            {/* Right Column: Sensor Evidence Table */}
            <div className="ai-diag-column">
              <section className="ai-diag-card">
                <div className="ai-diag-card__header">
                  <span className="ai-diag-card__num">03</span>
                  <h4>Telemetry Sensor Deviation Matrix</h4>
                </div>
                <div className="ai-diag-table-container">
                  <table className="ai-diag-table">
                    <thead>
                      <tr>
                        <th>Channel</th>
                        <th>Min</th>
                        <th>Mean</th>
                        <th>Max</th>
                        <th>Trend Δ</th>
                        <th>Nominal</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {channelStats.map((c) => (
                        <tr
                          key={c.channel}
                          className={c.status === "CRITICAL" ? "row-critical" : c.status === "WARNING" ? "row-warning" : ""}
                        >
                          <td className="cell-channel">
                            <span className="channel-indicator" />
                            {c.channel}
                          </td>
                          <td>{c.min.toFixed(1)}</td>
                          <td>{c.mean.toFixed(1)}</td>
                          <td>{c.max.toFixed(1)}</td>
                          <td className={c.delta > 0 ? "trend-up" : c.delta < 0 ? "trend-down" : ""}>
                            {c.delta > 0 ? `+${c.delta.toFixed(1)}` : c.delta.toFixed(1)}
                          </td>
                          <td className="cell-nominal">{c.nominal}</td>
                          <td>
                            <span className={`status-pill status-pill--${c.status.toLowerCase()}`}>
                              {c.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* Maintenance Directive */}
              <section className="ai-diag-card">
                <div className="ai-diag-card__header">
                  <span className="ai-diag-card__num">04</span>
                  <h4>Post-Flight Maintenance Directives</h4>
                </div>
                <div className="ai-diag-card__body">
                  <div className="ai-diag-maintenance-box">
                    <p>
                      <strong>Pre-Turnaround Inspection Required:</strong> Immediate borescope inspection of cylinder liners and fuel rail leak test prior to subsequent sortie.
                    </p>
                    <p className="text-muted">
                      Log telemetry seed <code>#{snapshot.seed}</code> and flight distance <code>{snapshot.flight_distance_km.toFixed(1)} km</code> in the aircraft engine maintenance records.
                    </p>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </div>
      ) : (
        <div className="ai-diag-empty-prompt">
          <div className="ai-diag-empty-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 8v4M12 16h.01" />
            </svg>
          </div>
          <h3>Awaiting Diagnostic Execution</h3>
          <p>
            Current Scenario: <strong>{scenarioClean}</strong> ({stageClean} stage). Click <strong>"Run AI Diagnostic"</strong> to perform automated spectral and deviation analysis on this 30-second telemetry snapshot.
          </p>
          <button
            type="button"
            className="ai-diag-btn ai-diag-btn--primary"
            onClick={handleGenerate}
            disabled={loading}
          >
            Run AI Diagnostic Now
          </button>
        </div>
      )}
    </div>
  );
}

function getActionDirectives(scenario: string, isCritical: boolean) {
  if (scenario.includes("Fuel")) {
    return [
      { title: "Engage Auxiliary Fuel Boost Pump", detail: "Switch secondary boost pump to ON to stabilize rail pressure." },
      { title: "Reduce Continuous Throttle Demand", detail: "Retard throttle to 4800 RPM to limit fuel demand and avoid vapor lock." },
      { title: "Declare Pan-Pan & Monitor Pressure Drop", detail: "If pressure drops below 2.0 bar, initiate divert to nearest airfield." },
    ];
  }
  if (scenario.includes("Cooling")) {
    return [
      { title: "Open Radiator Cowl Flaps", detail: "Extend air cooling flaps to maximum aperture immediately." },
      { title: "Reduce Engine Climb Rate", detail: "Level off to increase ram air airspeed and decrease thermal heat rejection." },
      { title: "Enrich Combustion Mixture", detail: "Allow additional fuel cooling through combustion chamber." },
    ];
  }
  if (scenario.includes("Oil")) {
    return [
      { title: "Prepare Immediate Glide / Forced Landing", detail: "Oil pressure loss risks catastrophic crankshaft seizure within 90 seconds." },
      { title: "Throttle to Minimum Sustaining Power", detail: "Reduce bearing friction loads and check for smoke trailing." },
      { title: "Squawk 7700 & Vector to Runway", detail: "Execute emergency landing checklist on nearest viable hard surface." },
    ];
  }
  if (scenario.includes("Cylinder") || scenario.includes("EGT")) {
    return [
      { title: "Check Ignition Circuit (Lane A/B)", detail: "Cycle ECU ignition lanes to test for spark plug fouling on Cylinder 2." },
      { title: "Adjust Mixture to Enrichen Lean Cylinders", detail: "Offset cylinder imbalance to prevent exhaust valve burn-through." },
      { title: "Limit Manifold Pressure to 32 inHg", detail: "Avoid high-power knock conditions while EGT spread remains elevated." },
    ];
  }
  if (isCritical) {
    return [
      { title: "Reduce Power Setting to 75% MCP", detail: "Protect engine core components from thermal and mechanical stress." },
      { title: "Monitor Dominant Channel Decay Rate", detail: "Verify whether telemetry stabilization occurs within 30 seconds." },
      { title: "Alert Air Traffic Control", detail: "Report engine telemetry advisory and stand by for priority approach." },
    ];
  }
  return [
    { title: "Maintain Standard Cruise Power", detail: "All cylinders and lubrication channels operating within Rotax 915 iS limits." },
    { title: "Periodic Cross-Check", detail: "Scan oil temperature and EGT balance at next 30-minute waypoint." },
    { title: "Continue Planned Navigation Route", detail: "No pilot or operator intervention required." },
  ];
}

function buildComprehensiveMarkdown(snapshot: any, stats: ChannelStat[]): string {
  const lines: string[] = [];
  lines.push(`# AERIS TELEMETRY HEALTH REPORT`);
  lines.push(`**Scenario:** ${snapshot.scenario}`);
  lines.push(`**Flight Stage:** ${snapshot.flight_stage} · **Distance:** ${snapshot.flight_distance_km.toFixed(1)} km`);
  lines.push(`**Health Score:** ${snapshot.health.toFixed(1)}% · **Status:** ${snapshot.status_label} · **Severity:** ${snapshot.severity_score.toFixed(2)}`);
  lines.push(`**Generated:** ${new Date().toISOString()} · **Seed:** ${snapshot.seed} · **Noise:** ${snapshot.noise_level.toFixed(1)}`);
  lines.push("");
  lines.push("## 1. Executive Fault Assessment");
  lines.push(`${snapshot.cluster_text} — ${snapshot.status_desc}`);
  if (snapshot.cluster_sub) lines.push(snapshot.cluster_sub);
  lines.push("");
  lines.push("## 2. Sensor Telemetry Deviation Matrix");
  lines.push("| Channel | Min | Mean | Max | Trend Δ | Nominal | Status |");
  lines.push("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |");
  for (const s of stats) {
    lines.push(`| ${s.channel} | ${s.min.toFixed(1)} | ${s.mean.toFixed(1)} | ${s.max.toFixed(1)} | ${s.delta.toFixed(1)} | ${s.nominal} | ${s.status} |`);
  }
  lines.push("");
  lines.push("## 3. Flight Crew & Ground Action Directives");
  const actions = getActionDirectives(snapshot.scenario, snapshot.status_label === "CRITICAL");
  actions.forEach((a, i) => {
    lines.push(`${i + 1}. **${a.title}**: ${a.detail}`);
  });
  lines.push("");
  lines.push("---");
  lines.push("*AERIS Digital Twin Engine Health Monitoring System · Rotax 915 iS*");
  return lines.join("\n");
}
