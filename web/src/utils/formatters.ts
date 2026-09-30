export interface FlightStageDef {
  index: number;
  name: string;
  startKm: number;
  endKm: number;
  color: string;
  description: string;
}

export const MISSION_STAGES: FlightStageDef[] = [
  { index: 1, name: "Pre-flight", startKm: 0, endKm: 5, color: "#64748b", description: "Engine start & pre-taxi check" },
  { index: 2, name: "Takeoff", startKm: 5, endKm: 15, color: "#f59e0b", description: "Maximum rated takeoff thrust" },
  { index: 3, name: "Climb", startKm: 15, endKm: 45, color: "#3b82f6", description: "Climb to assigned cruise flight level" },
  { index: 4, name: "Cruise", startKm: 45, endKm: 240, color: "#06b6d4", description: "Nominal en-route cruise power" },
  { index: 5, name: "Loiter", startKm: 240, endKm: 260, color: "#a855f7", description: "Mission target area loiter" },
  { index: 6, name: "Descent", startKm: 260, endKm: 290, color: "#f97316", description: "Descent toward approach gate" },
  { index: 7, name: "Landing", startKm: 290, endKm: 300, color: "#10b981", description: "Final approach, touchdown & rollout" },
];

/**
 * Strips numeric prefix such as "4. Cruise" -> "Cruise".
 */
export function cleanFlightStage(stage: string | undefined | null): string {
  if (!stage) return "Unknown";
  const match = stage.match(/^\d+\.\s*(.+)$/);
  return match ? match[1].trim() : stage.trim();
}

/**
 * Returns the stage definition matching distance or stage name.
 */
export function getFlightStageByDistance(distanceKm: number): FlightStageDef {
  const d = Math.max(0, Math.min(300, distanceKm));
  const found = MISSION_STAGES.find((s) => d >= s.startKm && d < s.endKm);
  return found ?? MISSION_STAGES[MISSION_STAGES.length - 1];
}

/**
 * Strips prefix like "1. Fuel Pressure Anomaly..." -> "Fuel Pressure Anomaly".
 */
export function cleanScenarioName(scenario: string | undefined | null): string {
  if (!scenario) return "Nominal Operation";
  const match = scenario.match(/^\d+\.\s*(.+)$/);
  return match ? match[1].trim() : scenario.trim();
}
