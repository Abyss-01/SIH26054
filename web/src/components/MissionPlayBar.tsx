import React from "react";
import { useDashboardStore } from "../store";

export default function MissionPlayBar() {
  const store = useDashboardStore();
  const { playing, flightDistance, params } = store;
  const [isDragging, setIsDragging] = React.useState(false);

  // Playback loop: advance 1 km/s to match the Streamlit demo's 1 Hz sample rate.
  React.useEffect(() => {
    if (!playing) return;
    const tick = () => {
      const next = Math.min(store.flightDistance + 1, 300);
      store.setFlightDistance(next);
      store.setParams({ flight_distance: next });
      void store.fetchSnapshot();
    };
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [playing, store]);

  const togglePlaying = () => store.setPlaying(!playing);
  const reset = () => {
    store.setPlaying(false);
    store.setFlightDistance(0);
    store.setParams({ flight_distance: 0 });
    void store.fetchSnapshot();
  };

  const handleScrub = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    store.setFlightDistance(val);
    store.setParams({ flight_distance: val });
    void store.fetchSnapshot();
  };

  const stage = React.useMemo(() => {
    const d = flightDistance;
    const stages = [
      { name: "Pre-flight", max: 5 },
      { name: "Takeoff", max: 15 },
      { name: "Climb", max: 45 },
      { name: "Cruise", max: 240 },
      { name: "Loiter", max: 260 },
      { name: "Descent", max: 290 },
      { name: "Landing", max: 300 },
    ];
    return stages.find((s) => d < s.max)?.name ?? "Landing";
  }, [flightDistance]);

  return (
    <div className="mission-play-bar">
      <div className="mission-play-bar__controls">
        <button className="mission-play-bar__button mission-play-bar__button--play" onClick={togglePlaying}>
          {playing ? <PauseIcon /> : <PlayIcon />}
          <span>{playing ? "Pause" : "Play"}</span>
        </button>
        <button className="mission-play-bar__button mission-play-bar__button--reset" onClick={reset}>
          <RewindIcon />
          <span>Reset</span>
        </button>
      </div>

      <div className="mission-play-bar__scrubber">
        <div className="mission-play-bar__scrubber-label">
          <span className="mission-play-bar__stage">{stage}</span>
          <span className="mission-play-bar__distance">
            {flightDistance.toFixed(1)} km / 300 km
          </span>
        </div>
        <div className="mission-play-bar__track">
          <input
            type="range"
            min="0"
            max="300"
            step="0.5"
            value={flightDistance}
            onChange={handleScrub}
            className="mission-play-bar__slider"
            onMouseDown={() => setIsDragging(true)}
            onMouseUp={() => setIsDragging(false)}
            onTouchStart={() => setIsDragging(true)}
            onTouchEnd={() => setIsDragging(false)}
          />
          <div className="mission-play-bar__track-fill" style={{ width: `${(flightDistance / 300) * 100}%` }} />
          <div className="mission-play-bar__track-marker" style={{ left: `${(flightDistance / 300) * 100}%` }} />
        </div>
        <div className="mission-play-bar__ticks">
          {[
            { label: "0", pos: 0 },
            { label: "50", pos: 50 },
            { label: "100", pos: 100 },
            { label: "150", pos: 150 },
            { label: "200", pos: 200 },
            { label: "250", pos: 250 },
            { label: "300", pos: 300 },
          ].map((t) => (
            <span
              key={t.label}
              className="mission-play-bar__tick"
              style={{ left: `${t.pos}%` }}
            >
              {t.label}
            </span>
          ))}
        </div>
        {!isDragging && (
          <p className="mission-play-bar__hint">
            Drag the slider to scrub through the mission — jump to any stage, not just play forward.
          </p>
        )}
      </div>
    </div>
  );
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
      <path d="M8 5v14l11-7z"/>
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true">
      <rect x="6" y="4" width="4" height="16" rx="1"/>
      <rect x="14" y="4" width="4" height="16" rx="1"/>
    </svg>
  );
}

function RewindIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
      <path d="M3 3v5h5"/>
    </svg>
  );
}
