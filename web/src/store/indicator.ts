import { create } from "zustand";

// Store for the playback indicator (mirrored from the dashboard store so the
/// sidebar pill can read it without subscribing to the whole dashboard state).

export interface PlaybackIndicatorState {
  playing: boolean;
  flightStage: string;
  setPlaying: (playing: boolean) => void;
}

export const usePlaybackIndicatorStore = create<PlaybackIndicatorState>((set) => ({
  playing: false,
  flightStage: "",
  setPlaying: (playing) => set({ playing }),
}));
