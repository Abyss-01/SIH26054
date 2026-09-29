# AERIS Snapshot API — deployment

A FastAPI service that wraps the existing SIH26054 Demo engine and exposes it
as a JSON API for the React dashboard.

## Quick start (local)

```bash
cd snapshot_api
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:api --host 0.0.0.0 --port 8000
```

The API needs the `Demo/` package on its Python path. When run from the
repo root with `PYTHONPATH=.`, the `Demo/` import in `app/engine.py` resolves.

```bash
# From the repo root:
PYTHONPATH=. uvicorn snapshot_api.app.main:api --host 0.0.0.0 --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check |
| GET | `/api/scenarios` | List of all scenario keys (including Auto guided tour) |
| POST | `/api/snapshot` | Generate a 30-second telemetry window |

### `POST /api/snapshot`

Request body:
```json
{
  "scenario": "Auto (Follow Flight Profile Stages)",
  "noise_level": 1.0,
  "sample_seed": 42,
  "flight_distance": 140.0
}
```

Response: a `SnapshotResponse` with `health`, `status_label`, `samples` (30
rows), `baseline`, `cluster_text`, `anomaly_scores`, `outlier_mask`,
`reference_bands`, `flight_stage`, `flight_distance_km`, and the rest of the
contract documented in `app/models.py`.

## CORS

The API sets `Access-Control-Allow-Origin` from the `ALLOWED_ORIGINS` env var
(comma-separated). By default this is `http://localhost:5173,http://localhost:3000`
(the common React dev server ports).

For production, set `ALLOWED_ORIGINS` to your Supabase Storage URL(s). If
`ALLOWED_ORIGINS` is empty, CORS is disabled and only same-origin calls work.

## Deployment

### Render

1. Push `snapshot_api/` to the GitHub repo.
2. Render → **New Web Service** → connect repo → pick `snapshot_api/` as root.
3. Runtime: Python 3. Build: `pip install -r requirements.txt`. Start:
   `uvicorn snapshot_api.app.main:api --host 0.0.0.0 --port $PORT`.
4. Set `ALLOWED_ORIGINS` in the Render dashboard to your Supabase Storage URL.
5. Deploy.

The `render.yaml` in this directory is a blueprint you can import instead of
clicking through the dashboard.

### Docker

Build from the repo root (so `Demo/` is available alongside `snapshot_api/`):

```bash
cd ..
docker build -f snapshot_api/Dockerfile -t areis-snapshot-api .
docker run -p 8000:8000 -e ALLOWED_ORIGINS="http://localhost:5173" areis-snapshot-api
```

The `Dockerfile` copies the whole repo so `Demo/` resolves via
`PYTHONPATH=/app`.

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated origins for CORS |
| `PORT` | `8000` | Listening port (Render sets this automatically) |

No API keys or secrets are required to run the engine API — it generates
synthetic data only. The Gemini key lives in the Supabase Edge Function (separate).

## Design notes

- The API is a thin wrapper. `app/engine.py` delegates to the unmodified
  `Demo.telemetry.generator.generate_telemetry_data` and serializes the result.
- The existing `Demo/tests/` suite (48 tests) still runs against the original
  code and still passes. The `snapshot_api/tests/` suite calls the API over HTTP
  and asserts the response shape.
- The response schema mirrors what `Demo/views/dashboard.py` already reads from
  the generator, so the React frontend can consume the same shape.
