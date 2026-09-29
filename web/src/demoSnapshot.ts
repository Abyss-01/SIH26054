import type { SnapshotRequest, SnapshotResponse, TelemetrySample } from "./types";

const columns = ["Time (s)", "Engine RPM", "Oil Pressure (bar)", "CHT", "MAP", "EGT Cyl 1 (°C)", "EGT Cyl 2 (°C)", "EGT Cyl 3 (°C)", "EGT Cyl 4 (°C)", "EGT Spread (°C)"];
type Fault = "nominal" | "fuel" | "cooling" | "sensor" | "gearbox" | "egt" | "oil" | "turbo";

function stageAt(distance: number) { return distance < 5 ? "Pre-flight" : distance < 15 ? "Takeoff" : distance < 45 ? "Climb" : distance < 240 ? "Cruise" : distance < 260 ? "Loiter" : distance < 290 ? "Descent" : "Landing"; }
function faultFor(scenario: string): Fault {
  if (scenario.includes("Fuel")) return "fuel";
  if (scenario.includes("Cooling Degradation")) return "cooling";
  if (scenario.includes("Sensor Drift")) return "sensor";
  if (scenario.includes("Gearbox")) return "gearbox";
  if (scenario.includes("EGT Cylinder")) return "egt";
  if (scenario.includes("Oil Pressure")) return "oil";
  return scenario.includes("Turbo") ? "turbo" : "nominal";
}

const summaries: Record<Fault, { channel: string; description: string }> = {
  nominal: { channel: "EGT Spread (°C)", description: "All monitored values remain within the nominal envelope." },
  fuel: { channel: "Engine RPM", description: "Fuel-delivery instability is reducing power consistency after anomaly onset." },
  cooling: { channel: "CHT", description: "Thermal loading is rising across the cooling circuit." },
  sensor: { channel: "CHT", description: "Coolant temperature sensor is drifting low relative to the thermal trend." },
  gearbox: { channel: "Engine RPM", description: "High-frequency drivetrain vibration is visible in the RPM signature." },
  egt: { channel: "EGT Cyl 2 (°C)", description: "Cylinder 2 combustion temperature is diverging from the other cylinders." },
  oil: { channel: "Oil Pressure (bar)", description: "Lubrication pressure is degrading below the nominal operating envelope." },
  turbo: { channel: "MAP", description: "Boost air-path collapse is reducing manifold pressure and delivered power." },
};

/** Deterministic local telemetry: every Streamlit fault preset has a visible signature. */
export function createDemoSnapshot(request: SnapshotRequest): SnapshotResponse {
  const fault = faultFor(request.scenario);
  const hasFault = fault !== "nominal";
  const samples: TelemetrySample[] = Array.from({ length: 30 }, (_, i) => {
    const wave = Math.sin((i + request.sample_seed) * 0.63) * request.noise_level;
    const active = Math.max(0, i - 14);
    let rpm = 5100 + Math.sin(i * 0.35) * 75 + wave * 25;
    let oil = 4.25 + wave * 0.12; let cht = 159 + Math.sin(i * 0.3) * 2 + wave; let map = 34.5 + Math.cos(i * 0.24) * 0.7;
    let egt1 = 700 + Math.cos(i * 0.5) * 4; let egt2 = 706 + wave * 5; let egt3 = 703 + Math.sin(i * 0.42) * 4; let egt4 = 701 + Math.cos(i * 0.37) * 3;
    if (fault === "fuel") { rpm -= active * 19; egt2 += active * 2.2; }
    if (fault === "cooling") { cht += active * 2.1; egt1 += active * 1.4; egt2 += active * 1.5; egt3 += active * 1.4; egt4 += active * 1.4; }
    if (fault === "sensor") cht -= active * 2.2;
    if (fault === "gearbox") rpm += active > 0 ? Math.sin(i * 8.5) * (55 + active * 10) : 0;
    if (fault === "egt") egt2 += active * 4.2;
    if (fault === "oil") oil -= active * 0.095;
    if (fault === "turbo") { map -= active * 0.14; rpm -= active * 23; }
    return { "Time (s)": i, "Engine RPM": rpm, "Oil Pressure (bar)": oil, CHT: cht, MAP: map, "EGT Cyl 1 (°C)": egt1, "EGT Cyl 2 (°C)": egt2, "EGT Cyl 3 (°C)": egt3, "EGT Cyl 4 (°C)": egt4, "EGT Spread (°C)": Math.max(egt1, egt2, egt3, egt4) - Math.min(egt1, egt2, egt3, egt4) };
  });
  const outlier_mask = samples.map((_, i) => hasFault && i >= 22);
  const outlier_count = outlier_mask.filter(Boolean).length;
  const status_label = outlier_count >= 7 ? "CRITICAL" : outlier_count ? "WARNING" : "NORMAL";
  const summary = summaries[fault];
  return {
    scenario: request.scenario, flight_stage: stageAt(request.flight_distance), flight_distance_km: request.flight_distance, noise_level: request.noise_level, seed: request.sample_seed, health: hasFault ? 61 : 98.4, status_label, status_class: status_label.toLowerCase(), status_desc: summary.description,
    cluster_text: hasFault ? `${summary.channel} anomaly cluster` : "Nominal operating cluster", cluster_sub: hasFault ? "Fault onset begins at 15 s; flagged samples begin at 22 s." : "Stable combustion and lubrication pattern.", is_outlier: outlier_count > 0, outlier_count, outlier_fraction: outlier_count / samples.length, severity_score: hasFault ? 0.78 : 0.03, dominant_channel: summary.channel,
    peak_egt_spread: Math.max(...samples.map((sample) => sample["EGT Spread (°C)"])), rul: null, columns, samples, baseline: undefined, anomaly_scores: samples.map((_, i) => hasFault && i >= 22 ? 2.7 + (i - 22) * 0.18 : 0.18 + i / 150), outlier_mask, anomaly_threshold: 2.5,
    reference_bands: { "Oil Pressure (bar)": { nominal: 4.25, min: 3.5, max: 5, tolerance: 0.75, unit: "bar" }, CHT: { nominal: 159, min: 140, max: 180, tolerance: 21, unit: "°C" }, MAP: { nominal: 34.5, min: 30, max: 38, tolerance: 4, unit: "inHg" }, "EGT Spread (°C)": { nominal: 8, min: 0, max: 25, tolerance: 17, unit: "°C" } }, generated_at: new Date().toISOString(),
  };
}
