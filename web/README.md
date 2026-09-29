# AERIS Dashboard — React frontend

A Vite + React + TypeScript dashboard that consumes the AERIS Snapshot API
(FastAPI service) and displays the UAV engine telemetry console for the
SIH26054 demo.

## What it is

This is the React/TypeScript frontend half of the "React + Supabase + FastAPI
API" architecture. The dashboard:
- Calls the FastAPI snapshot service to generate 30-second telemetry windows
- Renders four-panel telemetry charts (Plotly), metric cards, flight path,
  mission controls, and an AI diagnostics tab
- Has a settings panel for Gemini API key configuration (key sent server-side
  to a Supabase Edge Function in production)

## Architecture

```
React app (this directory)        FastAPI service (snapshot_api/)    Gemini
───────────────────────────       ─────────────────────────────   ──────
Vite dev server / static build    uvicorn on Render (or any host)   (Google)
  │                                   │
  │  POST /api/snapshot              │
  │  GET  /api/scenarios             │
  │  GET  /health                    │
  │                                   │
  └─ hosted on Supabase Storage ─────┘
```

The React app and the FastAPI service are separate deployables:
- React bundle → Supabase Storage (static hosting, shareable URL)
- FastAPI service → Render (or any Python host)
- Gemini key → Supabase Edge Function (Deno, server-side)

## Setup

```bash
cd web
npm install
cp .env.example .env          # edit VITE_API_BASE_URL if the API isn't on localhost:8000
npm run dev
```

Then open http://localhost:5173. The dashboard will try to reach the snapshot
API at the configured base URL and generate an initial snapshot on load.

## Prerequisites

- A running snapshot API (the FastAPI service in `snapshot_api/`). For local
  dev, run it alongside the React app:
    ```bash
    # From the repo root:
    PYTHONPATH=. uvicorn snapshot_api.app.main:api --host 0.0.0.0 --port 8000
    ```
- Node 18+ and npm (or pnpm / yarn) for the React dev server.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start the Vite dev server on http://localhost:5173 |
| `npm run build` | Type-check and build the production bundle to `dist/` |
| `npm run preview` | Serve the built bundle locally for preview |

## State management

The app uses Zustand for lightweight state. Three stores:

- `store/dashboard.ts` — snapshot, params, loading, error, playback state
- `store/review.ts` — AI diagnostics markdown and live/fallback flag
- `store/settings.ts` — Gemini API key, selected model, connection test state

## API contract

The types in `src/types/index.ts` are the source of truth for the snapshot
shape. They mirror the Pydantic `SnapshotResponse` in
`snapshot_api/app/models.py` — keep them in sync.

Key fields:

- `samples[]` — 30 telemetry rows, each with Time (s), Oil Pressure, Engine RPM,
  EGT Cyl 1–4, EGT Spread
- `baseline[]` — nominal values for the same window (present in guided-tour mode)
- `health` — 0–100 score
- `status_label` — NORMAL / WARNING / CRITICAL
- `cluster_text` / `cluster_sub` — cluster assessment prose
- `anomaly_scores[]` / `outlier_mask[]` — per-sample anomaly info
- `reference_bands` — optional channel reference bands (when the engine provides them)

## Supabase deployment

See `supabase-deploy.md` for the step-by-step.

## Share it

The completed Vite build is a static site, so it can be shared from Vercel,
Netlify, Cloudflare Pages, or any static host. The quickest route is in
[SHARING.md](./SHARING.md). Deploy the snapshot API first, then set
`VITE_API_BASE_URL` to its public HTTPS URL while deploying `web/`.

## Notes

- The Gemini API key is **never stored in the browser**. The settings panel
  keeps it in memory only; in production it is sent server-to-server to the
  Supabase Edge Function.
- The telemetry chart uses `react-plotly.js` (Plotly.js under the hood) to match
  the existing Streamlit dashboard's chart style.
- The mission controls advance at 1 Hz (1 km per second) to match the Streamlit
  demo's sample rate.
