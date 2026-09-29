/// Environment configuration for the AERIS dashboard.
///
/// All environment variables are prefixed with VITE_ so Vite embeds them into
/// the client bundle at build time. Set these in a .env file (local dev) or in
/// the Supabase Storage redirect / site settings (production).

/// Base URL of the deployed FastAPI snapshot service.
/// Local dev: http://localhost:8000
/// Render deploy: https://<service>.onrender.com
export const API_BASE_URL =
  (window as unknown as { env?: { VITE_API_BASE_URL?: string } }).env?.VITE_API_BASE_URL ??
  "http://localhost:8000";

// How long (ms) to wait for the snapshot endpoint before showing a network error.
export const SNAPSHOT_TIMEOUT_MS = 15_000;

// Default scenario when the dashboard first loads.
export const DEFAULT_SCENARIO = "Auto (Follow Flight Profile Stages)";

// Flight distance envelope (km). The slider runs 0-300; the engine derives the
// flight stage from this value.
export const FLIGHT_DISTANCE_MIN = 0;
export const FLIGHT_DISTANCE_MAX = 300;
export const FLIGHT_DISTANCE_STEP = 0.5;
export const FLIGHT_DISTANCE_DEFAULT = 140;

// Noise level envelope. 0 = deterministic, higher = more sensor noise.
export const NOISE_MIN = 0;
export const NOISE_MAX = 2;
export const NOISE_STEP = 0.1;
export const NOISE_DEFAULT = 1.0;

// Random seed for the telemetry window. Same seed + same params = same window.
export const SEED_MIN = 0;
export const SEED_MAX = 10000;
export const SEED_DEFAULT = 42;
