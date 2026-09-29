/// API client for the AERIS Snapshot API.
///
/// Base URL is read from Vite's import.meta.env so the same build can point at a
/// local dev server or the deployed Render service.
///
/// The React app and the FastAPI service are separate deployables:
///   - React bundle  -> Supabase Storage (static hosting)
///   - FastAPI service -> Render (or any Python host)
///
/// They talk over HTTPS, so CORS on the API side is the only cross-origin concern
/// (configured via ALLOWED_ORIGINS in snapshot_api/app/main.py).
///
import type { Scenario, SnapshotRequest, SnapshotResponse } from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) {
    throw new ApiError(`GET ${path} failed: ${response.status}`, response.status);
  }
  return response.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(`POST ${path} failed: ${response.status} ${text}`, response.status);
  }
  return response.json();
}

// ---- Health ----

export async function checkHealth(): Promise<{ status: string; service: string }> {
  return get("/health");
}

// ---- Scenarios ----

export interface ScenarioListItem {
  label: string;
  value: string;
}

export async function listScenarios(): Promise<ScenarioListItem[]> {
  const values = await get<string[]>("/api/scenarios");
  // The API returns the scenario *values* (the engine-accepted keys). We mirror
  // the labels from SCENARIOS so the UI speaks human-readable names.
  return values.map((value) => ({
    label: SCENARIO_LABEL_MAP[value as Scenario] ?? value,
    value,
  }));
}

// ---- Snapshot ----

export async function fetchSnapshot(request: SnapshotRequest): Promise<SnapshotResponse> {
  const response = await post<SnapshotResponse | ServerSnapshot>("/api/snapshot", request);
  return "samples" in response ? response : flattenSnapshot(response);
}

/** Converts the existing Python API's grouped response into the UI's flat shape. */
interface ServerSnapshot {
  meta: Record<string, unknown>;
  health: Record<string, unknown>;
  cluster: Record<string, unknown>;
  channels: { columns: string[]; observed: SnapshotResponse["samples"]; baseline?: SnapshotResponse["samples"] };
  anomaly: { scores: number[]; mask: boolean[]; threshold: number };
  reference_bands: SnapshotResponse["reference_bands"];
  rul: number | null;
}

function flattenSnapshot(source: ServerSnapshot): SnapshotResponse {
  const meta = source.meta;
  const health = source.health;
  const cluster = source.cluster;
  return {
    scenario: meta.scenario as Scenario,
    flight_stage: String(meta.flight_stage), flight_distance_km: Number(meta.flight_distance_km),
    noise_level: Number(meta.noise_level), seed: Number(meta.seed), health: Number(health.score),
    status_label: health.status as SnapshotResponse["status_label"], status_class: String(health.status_class), status_desc: String(health.description),
    cluster_text: String(cluster.text), cluster_sub: String(cluster.sub ?? ""), cluster_color: String(cluster.color ?? ""),
    is_outlier: Number(health.outlier_count) > 0, outlier_count: Number(health.outlier_count), outlier_fraction: Number(health.outlier_fraction),
    severity_score: Number(health.severity), dominant_channel: String(health.dominant_channel), peak_egt_spread: Number(health.peak_egt_spread),
    rul: source.rul, columns: source.channels.columns, samples: source.channels.observed, baseline: source.channels.baseline,
    anomaly_scores: source.anomaly.scores, outlier_mask: source.anomaly.mask, anomaly_threshold: source.anomaly.threshold,
    reference_bands: source.reference_bands, generated_at: String(meta.generated_at),
  };
}

// ---- Scenario label mapping ----
// Mirrors SCENARIO_LABELS in Demo/config/scenarios.py so the UI uses the same
// human-readable names the Streamlit app does. Keep these in sync.

const SCENARIO_LABEL_MAP: Readonly<Record<Scenario, string>> = {
  "Auto (Follow Flight Profile Stages)": "Guided flight tour",
  "Nominal Operation (No Anomaly)": "Nominal operation",
  "1. Fuel Pressure Anomaly (2.5 - 3.5 bar instability)": "Fuel pressure instability",
  "2. Cooling Degradation / Thermal Overheating": "Cooling degradation",
  "3. Coolant Sensor Drift / False-Low Reading": "Temperature sensor drift",
  "4. Gearbox High-Frequency Vibration Anomaly": "Elevated vibration",
  "5. EGT Cylinder 2 Combustion Imbalance": "Cylinder 2 EGT imbalance",
  "6. Oil Pressure Loss / Lubrication Degradation": "Oil pressure loss",
  "7. Turbocharger Boost Air-Path Collapse": "Boost pressure loss",
};
