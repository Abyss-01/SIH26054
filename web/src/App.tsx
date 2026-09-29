import { useEffect } from "react";
import { useDashboardStore } from "./store";
import { checkHealth, listScenarios } from "./api";
import Layout from "./components/Layout";
import TabBar from "./components/TabBar";

export default function App() {
  const { fetchSnapshot } = useDashboardStore();

  // On mount: verify the API is reachable, load the scenario list (informational),
  // and generate the initial snapshot from the default parameters.
  useEffect(() => {
    async function init() {
      try {
        const health = await checkHealth();
        console.log("[AERIS] API health:", health);
      } catch (err) {
        console.warn("[AERIS] API not reachable:", err);
      }
      try {
        const scenarios = await listScenarios();
        console.log("[AERIS] Loaded", scenarios.length, "scenarios");
      } catch (err) {
        console.warn("[AERIS] Failed to load scenarios:", err);
      }
    }
    init();
  }, []);

  // Generate the initial snapshot on first render.
  useEffect(() => {
    fetchSnapshot();
  }, []);

  return <Layout><TabBar /></Layout>;
}
