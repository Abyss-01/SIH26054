import { create } from "zustand";

// Settings store — Gemini API key and model selection. The key is kept in
// memory only (never persisted to localStorage or the bundle). In the deployed
// app, the key is stored server-side in the Supabase Edge Function's
// environment variables, and the React app never sees it.

interface SettingsState {
  apiKey: string;
  selectedModel: string;
  models: string[];
  setApiKey: (key: string) => void;
  setSelectedModel: (model: string) => void;
  setModels: (models: string[]) => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  apiKey: "",
  selectedModel: "",
  models: [],
  setApiKey: (key) => set({ apiKey: key }),
  setSelectedModel: (model) => set({ selectedModel: model }),
  setModels: (models) => set({ models }),
}));
