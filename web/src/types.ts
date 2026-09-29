/// Types that mirror the FastAPI snapshot API contract.
///
/// These are derived from `snapshot_api/app/models.py` (the Pydantic schemas)
/// and must stay in sync with the API. The API validates requests against
/// Scenario and SnapshotRequest; the response is SnapshotResponse.

export type Scenario =
  | "Auto (Follow Flight Profile Stages)"
  | "Nominal Operation (No Anomaly)"
  | "1. Fuel Pressure Anomaly (2.5 - 3.5 bar instability)"
  | "2. Cooling Degradation / Thermal Overheating"
  | "3. Coolant Sensor Drift / False-Low Reading"
  | "4. Gearbox High-Frequency Vibration Anomaly"
  | "5. EGT Cylinder 2 Combustion Imbalance"
  | "6. Oil Pressure Loss / Lubrication Degradation"
  | "7. Turbocharger Boost Air-Path Collapse";

export type StatusLabel = "NORMAL" | "WARNING" | "CRITICAL";

export interface ReferenceBand {
  nominal: number;
  min: number;
  max: number;
  tolerance: number;
  unit: string;
}

export interface TelemetrySample {
  "Time (s)": number;
  "Engine RPM": number;
  "Oil Pressure (bar)": number;
  "EGT Cyl 1 (°C)": number;
  "EGT Cyl 2 (°C)": number;
  "EGT Cyl 3 (°C)": number;
  "EGT Cyl 4 (°C)": number;
  "EGT Spread (°C)": number;
  CHT?: number;
  MAP?: number;
}

export interface SnapshotRequest {
  scenario: Scenario;
  noise_level: number;
  sample_seed: number;
  flight_distance: number;
}

export interface SnapshotResponse {
  scenario: Scenario;
  flight_stage: string;
  flight_distance_km: number;
  noise_level: number;
  seed: number;
  health: number;
  status_label: StatusLabel;
  status_class: string;
  status_desc: string;
  cluster_text: string;
  cluster_sub?: string;
  cluster_color?: string;
  is_outlier: boolean;
  outlier_count: number;
  outlier_fraction: number;
  severity_score: number;
  dominant_channel: string;
  peak_egt_spread: number;
  rul: number | null;
  columns: string[];
  samples: TelemetrySample[];
  baseline?: TelemetrySample[];
  anomaly_scores: number[];
  outlier_mask: boolean[];
  anomaly_threshold: number;
  reference_bands: Record<string, ReferenceBand>;
  generated_at: string;
}

// Scenario list for the select dropdown.
// `value` is the exact scenario key the API validates against (from
// Demo/config/scenarios.py::SCENARIO_OPTIONS); `label` is the human-readable
// name from SCENARIO_LABELS.

export const SCENARIOS: Readonly<{ value: Scenario; label: string }[]> = [
  { value: "Auto (Follow Flight Profile Stages)", label: "Guided flight tour" },
  { value: "Nominal Operation (No Anomaly)", label: "Nominal operation" },
  { value: "1. Fuel Pressure Anomaly (2.5 - 3.5 bar instability)", label: "Fuel pressure instability" },
  { value: "2. Cooling Degradation / Thermal Overheating", label: "Cooling degradation" },
  { value: "3. Coolant Sensor Drift / False-Low Reading", label: "Temperature sensor drift" },
  { value: "4. Gearbox High-Frequency Vibration Anomaly", label: "Elevated vibration" },
  { value: "5. EGT Cylinder 2 Combustion Imbalance", label: "Cylinder 2 EGT imbalance" },
  { value: "6. Oil Pressure Loss / Lubrication Degradation", label: "Oil pressure loss" },
  { value: "7. Turbocharger Boost Air-Path Collapse", label: "Boost pressure loss" },
];

export const FLIGHT_STAGES = [
  "Pre-flight",
  "Takeoff",
  "Climb",
  "Cruise",
  "Loiter",
  "Descent",
  "Landing",
] as const;

export type FlightStage = (typeof FLIGHT_STAGES)[number];
