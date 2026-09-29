import React from "react";
import { useDashboardStore } from "../store";
import { useReviewStore } from "../store";

export default function AIDiagnosticView() {
  const { snapshot, params } = useDashboardStore();
  const { review, live, loading, error, setReview, setLoading, setError, clearReview } = useReviewStore();
  const [generated, setGenerated] = React.useState(false);

  const handleGenerate = async () => {
    if (!snapshot) return;
    setLoading(true);
    setError(null);
    try {
      // In production, call the Supabase Edge Function:
      //   const { data } = await supabase.functions.invoke('gemini-review', {
      //     body: buildGeminiRequest(snapshot),
      //   });
      // For now, generate a local fallback summary.
      await new Promise((r) => setTimeout(r, 600));
      const markdown = buildFallbackSummary(snapshot);
      setReview({ markdown, live: false });
      setGenerated(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate review");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!review) return;
    const blob = new Blob([review.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `areis-review-${params.sample_seed}-${params.flight_distance}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!snapshot) {
    return <EmptyState message="Load a snapshot to generate an AI review." />;
  }

  return (
    <div className="tab-panel">
      <div className="ai-diagnostics">
        <div className="ai-diagnostics__header">
          <h3 className="ai-diagnostics__title">AI Diagnostics</h3>
          <div className="ai-diagnostics__actions">
            <button
              className="ai-diagnostics__button"
              disabled={loading}
              onClick={handleGenerate}
            >
              {loading ? "Generating…" : generated ? "Regenerate Review" : "Generate Telemetry Review"}
            </button>
            {review && (
              <>
                <button
                  className="ai-diagnostics__button ai-diagnostics__button--secondary"
                  onClick={handleDownload}
                >
                  Download Review
                </button>
                <button
                  className="ai-diagnostics__button ai-diagnostics__button--secondary"
                  onClick={() => { clearReview(); setGenerated(false); }}
                >
                  Clear
                </button>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="ai-diagnostics__error">{error}</div>
        )}

        {review ? (
          <div className="ai-diagnostics__review">
            <div className="ai-diagnostics__badge" data-live={live}>
              {live ? "Live — Gemini reviewed" : "Local fallback summary"}
            </div>
            <div
              className="ai-diagnostics__content"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(review.markdown) }}
            />
          </div>
        ) : (
          <div className="ai-diagnostics__placeholder">
            <p>No review generated yet. Click "Generate Telemetry Review" to analyze the current snapshot.</p>
            <p className="ai-diagnostics__note">
              {params.scenario === "Nominal Operation (No Anomaly)"
                ? "The current scenario is nominal — the review will describe expected engine behavior."
                : "The review analyzes the injected fault pattern in the current snapshot."}
            </p>
          </div>
        )}
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

function buildFallbackSummary(snapshot: NonNullable<ReturnType<typeof useDashboardStore.getState>["snapshot"]>): string {
  const lines: string[] = [];
  lines.push(`# Telemetry Review — ${snapshot.scenario}`);
  lines.push("");
  lines.push(`**Flight stage:** ${snapshot.flight_stage} · **Distance:** ${snapshot.flight_distance_km.toFixed(1)} km`);
  lines.push(`**Health score:** ${snapshot.health.toFixed(0)} · **Status:** ${snapshot.status_label}`);
  lines.push(`**Samples:** ${snapshot.samples.length} · **Seed:** ${snapshot.seed} · **Noise:** ${snapshot.noise_level.toFixed(1)}`);
  lines.push("");
  lines.push("## Cluster Assessment");
  lines.push("");
  lines.push(snapshot.cluster_text);
  if (snapshot.cluster_sub) lines.push(snapshot.cluster_sub);
  lines.push("");
  lines.push("## Sensor Summary");
  lines.push("");
  lines.push("| Channel | Min | Mean | Max | Δ | Samples |");
  lines.push("|---------|-----|------|-----|---|---------|");

  const channels = ["Engine RPM", "Oil Pressure (bar)", "EGT Cyl 1 (°C)", "EGT Cyl 2 (°C)", "EGT Cyl 3 (°C)", "EGT Cyl 4 (°C)", "EGT Spread (°C)"];
  for (const ch of channels) {
    const vals = snapshot.samples
      .map((r) => r[ch as keyof typeof r])
      .filter((v): v is number => typeof v === "number" && Number.isFinite(v));
    if (vals.length === 0) continue;
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
    const change = vals.length >= 2 ? vals.at(-1)! - vals[0]! : 0;
    lines.push(
      `| ${ch} | ${min.toFixed(2)} | ${mean.toFixed(2)} | ${max.toFixed(2)} | ${change.toFixed(2)} | ${vals.length} |`
    );
  }
  lines.push("");
  lines.push("## Anomaly Summary");
  lines.push("");
  lines.push(`- **Outliers detected:** ${snapshot.outlier_count} (${(snapshot.outlier_fraction * 100).toFixed(0)}% of samples)`);
  lines.push(`- **Severity score:** ${snapshot.severity_score.toFixed(2)}`);
  lines.push(`- **Dominant channel:** ${snapshot.dominant_channel}`);
  lines.push(`- **Peak EGT spread:** ${snapshot.peak_egt_spread.toFixed(1)} °C`);
  lines.push("");
  lines.push("---");
  lines.push("");
  lines.push("*Local evidence summary — no live API call was made.*");
  lines.push("");
  lines.push("*This is a synthetic simulation for demonstration purposes. Health scores and anomaly flags are computed from the simulated telemetry window and do not represent real engine data.*");
  return lines.join("\n");
}

function renderMarkdown(md: string): string {
  // Very simple markdown → HTML for the demo. In production, use a proper
  // markdown renderer (marked, react-markdown, etc.).
  return md
    .split("\n").map((line) => {
      if (line.startsWith("# ")) return `<h1>${line.slice(2)}</h1>`;
      if (line.startsWith("## ")) return `<h2>${line.slice(3)}</h2>`;
      if (line.startsWith("### ")) return `<h3>${line.slice(4)}</h3>`;
      if (line.startsWith("- **")) {
        const m = line.match(/^- \*\*(.+?)\*\*: (.+)$/);
        if (m) return `<li><strong>${m[1]}</strong>: ${m[2]}</li>`;
      }
      if (line.match(/^\|.*\|$/)) {
        if (line.includes("---")) return "";
        const cells = line.slice(1, -1).split("|").map((c) => c.trim());
        return `<tr>${cells.map((c) => `<td>${c}</td>`).join("")}</tr>`;
      }
      if (line.startsWith("*") && line.endsWith("*")) {
        return `<em>${line.slice(1, -1)}</em>`;
      }
      if (line.match(/\*\*(.+?)\*\*/)) {
        return line.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
      }
      if (line.trim() === "") return "<br/>";
      return `<p>${line}</p>`;
    }).join("\n");
}
