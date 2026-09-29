import type { SnapshotRequest, SnapshotResponse, TelemetrySample } from "./types";

const columns = ["Time (s)", "Engine RPM", "Oil Pressure (bar)", "EGT Cyl 1 (°C)", "EGT Cyl 2 (°C)", "EGT Cyl 3 (°C)", "EGT Cyl 4 (°C)", "EGT Spread (°C)"];

function stageAt(distance: number) {
  if (distance < 5) return "Pre-flight";
  if (distance < 15) return "Takeoff";
  if (distance < 45) return "Climb";
  if (distance < 240) return "Cruise";
  if (distance < 260) return "Loiter";
  if (distance < 290) return "Descent";
  return "Landing";
}

/** A deterministic built-in data source so the shared static demo never needs a server to render. */
export function createDemoSnapshot(request: SnapshotRequest): SnapshotResponse {
  const hasOilFault = request.scenario.includes("Oil Pressure");
  const hasEgtFault = request.scenario.includes("EGT Cylinder");
  const hasCoolingFault = request.scenario.includes("Cooling");
  const hasFault = hasOilFault || hasEgtFault || hasCoolingFault || request.scenario.includes("Fuel") || request.scenario.includes("Turbo") || request.scenario.includes("Gearbox");
  const samples: TelemetrySample[] = Array.from({ length: 30 }, (_, i) => {
    const wave = Math.sin((i + request.sample_seed) * 0.63) * request.noise_level;
    const oil = 4.25 + wave * 0.12 - (hasOilFault && i > 14 ? (i - 14) * 0.09 : 0);
    const egt2 = 706 + wave * 5 + (hasEgtFault && i > 12 ? (i - 12) * 3.8 : 0);
    const egt1 = 700 + Math.cos(i * 0.5) * 4 + (hasCoolingFault ? i * 1.2 : 0);
    const egt3 = 703 + Math.sin(i * 0.42) * 4 + (hasCoolingFault ? i * 1.1 : 0);
    const egt4 = 701 + Math.cos(i * 0.37) * 3 + (hasCoolingFault ? i * 1.15 : 0);
    return {
      "Time (s)": i,
      "Engine RPM": 5100 + Math.sin(i * 0.35) * 75 + wave * 25,
      "Oil Pressure (bar)": oil,
      "EGT Cyl 1 (°C)": egt1,
      "EGT Cyl 2 (°C)": egt2,
      "EGT Cyl 3 (°C)": egt3,
      "EGT Cyl 4 (°C)": egt4,
      "EGT Spread (°C)": Math.max(egt1, egt2, egt3, egt4) - Math.min(egt1, egt2, egt3, egt4),
    };
  });
  const outlier_mask = samples.map((sample, i) => hasFault && i > 18 && (sample["EGT Spread (°C)"] > 18 || sample["Oil Pressure (bar)"] < 3.6));
  const outlier_count = outlier_mask.filter(Boolean).length;
  const status_label = outlier_count > 6 ? "CRITICAL" : outlier_count ? "WARNING" : "NORMAL";
  const health = outlier_count ? Math.max(56, 92 - outlier_count * 3) : 98.4;

  return {
    scenario: request.scenario, flight_stage: stageAt(request.flight_distance), flight_distance_km: request.flight_distance,
    noise_level: request.noise_level, seed: request.sample_seed, health, status_label,
    status_class: status_label.toLowerCase(), status_desc: hasFault ? "Synthetic fault signature detected." : "All monitored values remain within the nominal envelope.",
    cluster_text: hasFault ? "Anomalous telemetry cluster" : "Nominal operating cluster", cluster_sub: hasFault ? "Review the highlighted samples and dominant channel." : "Stable combustion and lubrication pattern.",
    is_outlier: outlier_count > 0, outlier_count, outlier_fraction: outlier_count / samples.length,
    severity_score: outlier_count / 10, dominant_channel: hasOilFault ? "Oil Pressure (bar)" : hasEgtFault ? "EGT Cyl 2 (°C)" : "EGT Spread (°C)",
    peak_egt_spread: Math.max(...samples.map((sample) => sample["EGT Spread (°C)"])), rul: null, columns, samples,
    baseline: undefined, anomaly_scores: outlier_mask.map((outlier, i) => outlier ? 3 + i / 20 : 0.3 + i / 100), outlier_mask,
    anomaly_threshold: 2.5,
    reference_bands: { "Oil Pressure (bar)": { nominal: 4.25, min: 3.5, max: 5, tolerance: 0.75, unit: "bar" }, "EGT Spread (°C)": { nominal: 8, min: 0, max: 25, tolerance: 17, unit: "°C" } },
    generated_at: new Date().toISOString(),
  };
}
