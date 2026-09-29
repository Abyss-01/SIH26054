import { create } from "zustand";

import type { SnapshotRequest, SnapshotResponse } from "../types";
import { ApiError, fetchSnapshot } from "../api";

// Shared dashboard state. The React tree reads from this store; the API client
// writes into it when a snapshot is fetched. Playback state lives here too so
// the mission scrubber and the telemetry view stay in sync.

export interface DashboardState {
  snapshot: SnapshotResponse | null;
  params: SnapshotRequest & { geminiApiKey?: string };
  loading: boolean;
  error: string | null;
  playing: boolean;
  flightDistance: number;

  setSnapshot: (snapshot: SnapshotResponse | null) => void;
  setParams: (params: Partial<SnapshotRequest & { geminiApiKey?: string }>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setPlaying: (playing: boolean) => void;
  setFlightDistance: (distance: number) => void;
  fetchSnapshot: () => Promise<void>;
}

const DEFAULT_PARAMS: SnapshotRequest & { geminiApiKey?: string } = {
  scenario: "Auto (Follow Flight Profile Stages)",
  noise_level: 1.0,
  sample_seed: 42,
  flight_distance: 140,
};

export const useDashboardStore = create<DashboardState>((set, get) => ({
  snapshot: null,
  params: DEFAULT_PARAMS,
  loading: false,
  error: null,
  playing: false,
  flightDistance: DEFAULT_PARAMS.flight_distance,

  setSnapshot: (snapshot) => set({ snapshot }),
  setParams: (params) => set({ params: { ...get().params, ...params } }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  setPlaying: (playing) => set({ playing }),
  setFlightDistance: (distance) => set({ flightDistance: distance }),

  fetchSnapshot: async () => {
    const { params } = get();
    set({ loading: true, error: null });
    try {
      const response = await fetchSnapshot(params);
      set({ snapshot: response, loading: false });
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to generate telemetry";
      set({ error: message, loading: false });
    }
  },
}));
