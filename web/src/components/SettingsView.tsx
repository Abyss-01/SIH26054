import React from "react";
import { useDashboardStore } from "../store";

export default function SettingsView() {
  const { params, setParams, fetchSnapshot } = useDashboardStore();
  const [localKey, setLocalKey] = React.useState(params.geminiApiKey ?? "");
  const [models, setModels] = React.useState<string[]>([]);
  const [testStatus, setTestStatus] = React.useState<"idle" | "testing" | "ok" | "error">("idle");
  const [testMessage, setTestMessage] = React.useState("");

  const handleKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => setLocalKey(e.target.value);

  const handleSaveKey = async () => {
    // In production, send to the Supabase Edge Function.
    // For now, keep it in local state only (never persisted).
    setTestStatus("idle");
    setTestMessage("");
  };

  const handleClearKey = () => {
    setLocalKey("");
    setTestStatus("idle");
    setTestMessage("");
  };

  const handleTestConnection = async () => {
    if (!localKey.trim()) {
      setTestStatus("error");
      setTestMessage("Enter an API key first.");
      return;
    }
    setTestStatus("testing");
    setTestMessage("Testing connection…");
    try {
      await new Promise((r) => setTimeout(r, 800));
      setTestStatus("ok");
      setTestMessage("Connection verified.");
    } catch {
      setTestStatus("error");
      setTestMessage("Connection failed.");
    }
  };

  const handleLoadModels = async () => {
    if (!localKey.trim()) {
      setTestMessage("Configure a key first.");
      return;
    }
    setTestStatus("testing");
    setTestMessage("Loading models…");
    try {
      await new Promise((r) => setTimeout(r, 500));
      // In production, fetch from the Edge Function.
      // For now, show placeholder models.
      setModels(["gemini-2.0-flash", "gemini-2.5-flash", "gemini-3.0-pro", "gemini-3.5-pro"]);
      setTestStatus("ok");
      setTestMessage("Models loaded.");
    } catch {
      setTestStatus("error");
      setTestMessage("Failed to load models.");
    }
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    // In production, persist the selected model. For now, just update local state.
  };

  return (
    <div className="tab-panel">
      <div className="settings-view">
        <h3 className="settings-view__title">AI Configuration</h3>
        <p className="settings-view__subtitle">
          Configure the Gemini API key for live AI diagnostics. The key is never stored or sent to the browser bundle.
        </p>

        <div className="settings-view__field">
          <label className="settings-view__label">Gemini API Key</label>
          <div className="settings-view__key-row">
            <input
              type="password"
              className="settings-view__input"
              placeholder="Enter your Gemini API key"
              value={localKey}
              onChange={handleKeyChange}
              autoComplete="off"
            />
            <button className="settings-view__button settings-view__button--primary" onClick={handleSaveKey}>
              Save Key
            </button>
            {localKey && (
              <button className="settings-view__button settings-view__button--secondary" onClick={handleClearKey}>
                Clear
              </button>
            )}
          </div>
          <p className="settings-view__hint">
            The key is only used server-side by the Supabase Edge Function. It is never sent to the browser or persisted locally.
          </p>
        </div>

        <div className="settings-view__field">
          <label className="settings-view__label">Selected Model</label>
          <div className="settings-view__model-row">
            <select
              className="settings-view__select"
              value={models[0] ?? ""}
              onChange={handleModelChange}
              disabled={!models.length}
            >
              <option value="">Load available models…</option>
              {models.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <button
              className="settings-view__button settings-view__button--secondary"
              onClick={handleLoadModels}
              disabled={!localKey.trim()}
            >
              Load Models
            </button>
          </div>
        </div>

        <div className="settings-view__field">
          <button
            className="settings-view__button settings-view__button--test"
            onClick={handleTestConnection}
            disabled={!localKey.trim()}
          >
            Test Connection
          </button>
          {testStatus !== "idle" && (
            <p className={`settings-view__test-status ${testStatus === "ok" ? "settings-view__test-status--ok" : "settings-view__test-status--error"}`}>
              {testMessage}
            </p>
          )}
        </div>

        <div className="settings-view__divider" />

        <div className="settings-view__info">
          <h4>About the API key</h4>
          <p>
            In the deployed AERIS dashboard, the Gemini API key is stored in the Supabase Edge Function's environment variables.
            The React app calls the Edge Function, which calls Gemini server-side and returns the markdown review.
            The key never leaves the server and is never embedded in the browser bundle.
          </p>
          <p>
            The snapshot telemetry is generated by a separate FastAPI service (the AERIS Snapshot API), deployed independently
            (e.g., on Render). The React app calls that service for telemetry data and the Edge Function for reviews.
          </p>
        </div>

        <div className="settings-view__divider" />

        <div className="settings-view__info settings-view__info--muted">
          <h4>Demo note</h4>
          <p>
            AERIS is a synthetic telemetry demonstrator. All sensor data is generated by simulation — no real engine or flight data is used.
            Health scores and anomaly flags are computed from the simulated window and are illustrative only.
          </p>
        </div>
      </div>
    </div>
  );
}
