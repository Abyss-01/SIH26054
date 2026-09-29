# Supabase deployment — AERIS Dashboard

Instructions for deploying the React dashboard to Supabase Storage and wiring
it to the deployed snapshot API.

## Overview

```
React bundle (this directory → dist/)  →  Supabase Storage (static hosting)
                                                         │
                                                         ▼
                                                  browser renders the dashboard
                                                         │
                                                         ▼
                                            Snapshot API (Render / any host)
                                            (POST /api/snapshot, GET /api/scenarios)
```

The React app is a static bundle. Supabase Storage serves it as a static site.
The app calls the FastAPI snapshot API over HTTPS from the browser.

## 1. Build the React app

```bash
cd web
npm ci                       # install dependencies
cp .env.example .env
# Edit .env: set VITE_API_BASE_URL to your deployed snapshot API URL
# e.g. VITE_API_BASE_URL=https://areis-snapshot-api.onrender.com
npm run build
```

This produces `web/dist/` — the static bundle to upload.

## 2. Create a Supabase project

1. Go to https://supabase.com and create a new project (free tier is fine).
2. Note the project ref (the slug in the URL, e.g. `areis-demo`).

## 3. Upload the bundle to Supabase Storage

Option A — via the dashboard:
1. In your Supabase project, go to **Storage**.
2. Create a new bucket called `areis` (or `dashboard`).
3. Set the bucket to **Public** (so it can be served as a static site).
4. Upload the contents of `web/dist/` to the bucket root.

Option B — via the CLI:
```bash
# Install the Supabase CLI if you don't have it:
npm install -g supabase

# Link to your project:
cd ..                    # repo root
supabase login
supabase link --project-ref <your-project-ref>

# Upload the built bundle:
supabase storage upload --bucket areis --no-verify web/dist/ web/dist/
```

## 4. Enable static site hosting

Supabase Storage can serve a bucket as a static site. In the dashboard:
1. Go to **Storage** → your bucket (`areis`).
2. Look for **Site** or **Static site** settings.
3. Enable static site hosting. The URL will be something like:
   `https://<project-ref>.supabase.co/storage/v1/object/public/areis/`

Alternatively, set up a redirect rule if your Supabase project has a custom
domain or you're using the Storage URL directly.

If static site hosting isn't available on your plan, you can:
- Use the Storage object URL directly (each file is individually accessible),
- Or put a reverse proxy / CDN in front of the bucket,
- Or deploy the built bundle to Netlify / Vercel instead (the bundle is just
  static files — it doesn't care where it's hosted).

## 5. Configure CORS on the snapshot API

The React app (hosted on Supabase) and the snapshot API (on Render) are
different origins. The API's `ALLOWED_ORIGINS` env var must include your
Supabase Storage URL.

In the Render dashboard for the snapshot API service:
- Set `ALLOWED_ORIGINS` to your Supabase Storage site URL, e.g.:
  ```
  https://<project-ref>.supabase.co/storage/v1/object/public/areis
  ```
- If you have multiple origins (dev + prod), comma-separate them.

The API's CORS middleware (in `snapshot_api/app/main.py`) reads this env var
and sets `Access-Control-Allow-Origin` accordingly.

## 6. Verify

1. Open the Supabase Storage site URL in a browser.
2. The dashboard should load and immediately call the snapshot API.
3. If the API is reachable, you'll see the telemetry console load with a
   synthetic mission window.
4. If the API is not reachable, you'll see an error panel in the dashboard
   (the app handles this gracefully and tells you what's wrong).

## 7. Gemini review (optional, next step)

The AI diagnostics tab currently generates a local fallback summary. To enable
live Gemini reviews:

1. Create a Supabase Edge Function (`supabase functions deploy gemini-review`)
2. Store your Gemini API key in Supabase secrets (`supabase secrets set GEMINI_API_KEY=...`)
3. The Edge Function calls Gemini server-side and returns markdown
4. Wire the React app's `AIDiagnosticPanel` to call the Edge Function instead
   of generating a local summary

See the Edge Function sketch in `src/components/AIDiagnosticPanel.tsx` comments
for the integration point.

## 8. Optional: persistence

If you want saved snapshots / reports:

1. Create a Postgres table in your Supabase project:
   ```sql
   CREATE TABLE snapshots (
     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     scenario TEXT NOT NULL,
     noise_level REAL NOT NULL,
     sample_seed INTEGER NOT NULL,
     flight_distance REAL NOT NULL,
     review TEXT,
     notes TEXT,
     created_at TIMESTAMPTZ DEFAULT now()
   );
   ```
2. Create an Edge Function or use the Supabase JS client to insert/retrieve.
3. Wire the React app's save/load UI to those endpoints.

For the demo, a stateless app (no persistence) is fine — the snapshot API
regenerates the same data for the same parameters, so "saving" is just
remembering the parameters.

## Troubleshooting

**Dashboard loads but shows "Unable to generate telemetry":**
- Check that `VITE_API_BASE_URL` in the React build points to a running API.
- Check that the API's `ALLOWED_ORIGINS` includes the Supabase Storage URL.
- Check the browser console for CORS errors.

**Charts don't render:**
- Verify `react-plotly.js` and `plotly.js` are installed (`npm ls react-plotly.js`).
- Check the browser console for Plotly errors.

**CORS errors in console:**
- The API's `ALLOWED_ORIGINS` doesn't include your Supabase URL.
- Set it in the Render dashboard and redeploy (or restart) the service.

**Snapshot API returns 400:**
- Check the request body matches the `SnapshotRequest` schema in
  `snapshot_api/app/models.py`.
- The `scenario` field must be one of the values from `GET /api/scenarios`.
