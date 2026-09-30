import React from "react";
import { useDashboardStore } from "../store";
import { MISSION_STAGES, cleanFlightStage, getFlightStageByDistance } from "../utils/formatters";

export default function MissionPlayBar() {
  const store = useDashboardStore();
  const { playing, flightDistance, snapshot } = store;
  const [speed, setSpeed] = React.useState<1 | 2 | 5>(1);

  // Playback timer loop
  React.useEffect(() => {
    if (!playing) return;
    const intervalMs = Math.round(1000 / speed);
    const id = setInterval(() => {
      const next = Math.min(300, Math.round((store.flightDistance + 1) * 10) / 10);
      store.setFlightDistance(next);
      store.setParams({ flight_distance: next });
      void store.fetchSnapshot();
      if (next >= 300) {
        store.setPlaying(false);
      }
    }, intervalMs);
    return () => clearInterval(id);
  }, [playing, speed, store]);

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

  const handleJumpToStage = (startKm: number) => {
    store.setFlightDistance(startKm);
    store.setParams({ flight_distance: startKm });
    void store.fetchSnapshot();
  };

  const currentStage = getFlightStageByDistance(flightDistance);
  const activeStageName = cleanFlightStage(snapshot?.flight_stage || currentStage.name);
  const progressPct = Math.min(100, Math.max(0, (flightDistance / 300) * 100));

  return (
    <div className="mission-controller">
      <div className="mission-controller__header">
        <div className="mission-controller__playback-group">
          <button
            type="button"
            className={`mission-controller__btn mission-controller__btn--play ${playing ? "mission-controller__btn--active" : ""}`}
            onClick={togglePlaying}
            title={playing ? "Pause mission progression" : "Play mission progression"}
          >
            {playing ? <PauseIcon /> : <PlayIcon />}
            <span>{playing ? "PAUSE" : "PLAY"}</span>
          </button>
          <button
            type="button"
            className="mission-controller__btn mission-controller__btn--subtle"
            onClick={reset}
            title="Reset flight distance to 0 km"
          >
            <RewindIcon />
            <span>RESET</span>
          </button>

          <div className="mission-controller__speeds">
            {([1, 2, 5] as const).map((s) => (
              <button
                key={s}
                type="button"
                className={`mission-controller__speed-btn ${speed === s ? "mission-controller__speed-btn--active" : ""}`}
                onClick={() => setSpeed(s)}
                title={`Playback speed ${s}x`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>

        <div className="mission-controller__status-group">
          <div className="mission-controller__stage-indicator">
            <span className="mission-controller__stage-tag">STAGE {currentStage.index}/7</span>
            <span className="mission-controller__stage-name" style={{ color: currentStage.color }}>
              {activeStageName}
            </span>
          </div>
          <div className="mission-controller__odometer">
            <span className="mission-controller__odometer-curr">{flightDistance.toFixed(1)} km</span>
            <span className="mission-controller__odometer-total">/ 300.0 km</span>
            <span className="mission-controller__odometer-pct">({progressPct.toFixed(0)}%)</span>
          </div>
        </div>
      </div>

      {/* Interactive Flight Stage Stepper */}
      <div className="mission-controller__stages" role="tablist" aria-label="Flight Stages">
        {MISSION_STAGES.map((s) => {
          const isCurrent = currentStage.index === s.index;
          const isPassed = flightDistance >= s.endKm;
          return (
            <button
              key={s.name}
              type="button"
              className={`mission-controller__stage-node ${isCurrent ? "mission-controller__stage-node--active" : ""} ${isPassed ? "mission-controller__stage-node--passed" : ""}`}
              onClick={() => handleJumpToStage(s.startKm)}
              title={`${s.name} (${s.startKm}–${s.endKm} km): ${s.description}. Click to jump.`}
            >
              <span className="mission-controller__node-idx" style={{ borderColor: isCurrent ? s.color : undefined }}>
                {s.index}
              </span>
              <span className="mission-controller__node-label">{s.name}</span>
              <span className="mission-controller__node-range">{s.startKm} km</span>
            </button>
          );
        })}
      </div>

      {/* Scrub Track with Integrated Colored Stage Bands */}
      <div className="mission-controller__scrubber-wrapper">
        <div className="mission-controller__track-bg">
          {MISSION_STAGES.map((s) => (
            <div
              key={s.name}
              className="mission-controller__track-segment"
              style={{
                left: `${(s.startKm / 300) * 100}%`,
                width: `${((s.endKm - s.startKm) / 300) * 100}%`,
                backgroundColor: s.color,
                opacity: currentStage.index === s.index ? 0.75 : 0.25,
              }}
            />
          ))}
          <div className="mission-controller__track-fill" style={{ width: `${progressPct}%` }} />
        </div>
        <input
          type="range"
          min="0"
          max="300"
          step="0.5"
          value={flightDistance}
          onChange={handleScrub}
          className="mission-controller__range-slider"
          aria-label="Mission distance scrubber"
        />
      </div>
    </div>
  );
}

function PlayIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true">
      <rect x="6" y="4" width="4" height="16" rx="1.5" />
      <rect x="14" y="4" width="4" height="16" rx="1.5" />
    </svg>
  );
}

function RewindIcon() {
  return (
    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
    </svg>
  );
}
