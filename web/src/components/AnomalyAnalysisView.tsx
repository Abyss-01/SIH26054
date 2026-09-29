import React from "react";
import { useDashboardStore } from "../store";

export default function AnomalyAnalysisView() {
  const { snapshot } = useDashboardStore();

  if (!snapshot) {
    return <EmptyState message="Load a snapshot to see anomaly analysis." />;
  }

  const { outlier_mask, anomaly_scores, outlier_count, outlier_fraction, anomaly_threshold, dominant_channel, severity_score, peak_egt_spread, samples } = snapshot;

  // Per-sample anomaly table (top outliers first).
  const outlierRows = React.useMemo(() => {
    const indexed = samples.map((s, i) => ({
      time: s["Time (s)"],
      score: anomaly_scores[i],
      isOutlier: outlier_mask[i],
      row: s,
    }));
    return indexed.filter((o) => o.isOutlier).sort((a, b) => b.score - a.score);
  }, [samples, anomaly_scores, outlier_mask]);

  // Channel-level anomaly scores.
  const channelScores = React.useMemo(() => {
    const channels = ["Engine RPM", "Oil Pressure (bar)", "CHT", "MAP", "EGT Cyl 1 (°C)", "EGT Cyl 2 (°C)", "EGT Cyl 3 (°C)", "EGT Cyl 4 (°C)", "EGT Spread (°C)"];
    return channels.map((ch) => {
      const vals = samples
        .map((s) => s[ch as keyof typeof s])
        .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
      if (vals.length === 0) return { channel: ch, mean: 0, std: 0, maxAbsDev: 0 };
      const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
      const variance = vals.reduce((a, b) => a + (b - mean) ** 2, 0) / vals.length;
      const std = Math.sqrt(variance);
      const maxAbsDev = Math.max(...vals.map((v) => Math.abs(v - mean)));
      return { channel: ch, mean, std, maxAbsDev };
    });
  }, [samples]);

  return (
    <div className="tab-panel">
      <div className="anomaly-analysis">
        <div className="anomaly-analysis__header">
          <h3 className="anomaly-analysis__title">Anomaly Analysis</h3>
        </div>

        <div className="anomaly-analysis__overview">
          <div className="anomaly-analysis__overview-grid">
            <div className="anomaly-analysis__stat-box">
              <span className="anomaly-analysis__stat-label">Anomaly threshold</span>
              <span className="anomaly-analysis__stat-value">{anomaly_threshold.toFixed(3)}</span>
              <span className="anomaly-analysis__stat-desc">Z-score cutoff for outlier classification</span>
            </div>
            <div className="anomaly-analysis__stat-box">
              <span className="anomaly-analysis__stat-label">Samples flagged</span>
              <span className="anomaly-analysis__stat-value anomaly-analysis__stat-value--critical">{outlier_count} / {samples.length}</span>
              <span className="anomaly-analysis__stat-desc">{(outlier_fraction * 100).toFixed(1)}% of telemetry samples</span>
            </div>
            <div className="anomaly-analysis__stat-box">
              <span className="anomaly-analysis__stat-label">Severity score</span>
              <span className="anomaly-analysis__stat-value">{severity_score.toFixed(2)}</span>
              <span className="anomaly-analysis__stat-desc">Aggregated anomaly severity (0 = nominal)</span>
            </div>
            <div className="anomaly-analysis__stat-box">
              <span className="anomaly-analysis__stat-label">Dominant channel</span>
              <span className="anomaly-analysis__stat-value">{dominant_channel}</span>
              <span className="anomaly-analysis__stat-desc">Channel with the strongest anomaly signal</span>
            </div>
            <div className="anomaly-analysis__stat-box">
              <span className="anomaly-analysis__stat-label">Peak EGT spread</span>
              <span className="anomaly-analysis__stat-value">{peak_egt_spread.toFixed(1)} °C</span>
              <span className="anomaly-analysis__stat-desc">Max cylinder EGT differential</span>
            </div>
          </div>
        </div>

        <div className="anomaly-analysis__section">
          <h4 className="anomaly-analysis__section-title">Per-Sample Outliers</h4>
          {outlierRows.length === 0 ? (
            <div className="anomaly-analysis__empty">
              <p>No outliers detected in this window.</p>
            </div>
          ) : (
            <div className="anomaly-analysis__table-scroll">
              <table className="anomaly-analysis__table">
                <thead>
                  <tr>
                    <th>Time (s)</th>
                    <th>Oil Pressure (bar)</th>
                    <th>Engine RPM</th>
                    <th>EGT Cyl 2 (°C)</th>
                    <th>EGT Spread (°C)</th>
                    <th>Anomaly Score</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {outlierRows.map((o) => (
                    <tr key={o.time} className="anomaly-analysis__row--outlier">
                      <td>{o.time.toFixed(1)}</td>
                      <td>{o.row["Oil Pressure (bar)"].toFixed(2)}</td>
                      <td>{o.row["Engine RPM"].toFixed(0)}</td>
                      <td>{o.row["EGT Cyl 2 (°C)"].toFixed(1)}</td>
                      <td>{o.row["EGT Spread (°C)"].toFixed(1)}</td>
                      <td>{o.score.toFixed(3)}</td>
                      <td className="anomaly-analysis__status">Outlier</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="anomaly-analysis__section">
          <h4 className="anomaly-analysis__section-title">Channel Deviation</h4>
          <p className="anomaly-analysis__desc">
            Maximum absolute deviation from the channel mean, across the 30-sample window.
            Channels with higher deviation contribute more to the severity score.
          </p>
          <div className="anomaly-analysis__channel-bar-scroll">
            <div className="anomaly-analysis__channel-bars">
              {channelScores.map((cs) => {
                const maxDev = Math.max(...channelScores.map((c) => c.maxAbsDev), 1);
                const pct = (cs.maxAbsDev / maxDev) * 100;
                return (
                  <div key={cs.channel} className="anomaly-analysis__channel-bar">
                    <div className="anomaly-analysis__channel-bar-label" title={cs.channel}>
                      {cs.channel}
                    </div>
                    <div className="anomaly-analysis__channel-bar-track">
                      <div
                        className="anomaly-analysis__channel-bar-fill"
                        style={{ width: `${Math.min(100, pct)}%` }}
                      />
                    </div>
                    <div className="anomaly-analysis__channel-bar-value">
                      {cs.maxAbsDev.toFixed(2)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="empty-state">
      <p>{message}</p>
    </div>
  );
}
