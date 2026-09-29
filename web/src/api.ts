// API barrel — re-exports everything from the typed client module.
//
// Import from this barrel:
//   import { fetchSnapshot, checkHealth } from "../api";
//
// …rather than from "../api/client" directly.

export { checkHealth, listScenarios, fetchSnapshot, ApiError } from "./api/client";
export type { ScenarioListItem } from "./api/client";
