# Share the AERIS demo

The dashboard is a static Vite site and the telemetry generator is a small
FastAPI service. Both need public URLs for a working shared demo.

## 1. Publish the snapshot API

Create a Render web service from this repository using
`snapshot_api/render.yaml`. Its build command installs the Python
dependencies and starts `snapshot_api.app.main:api`.

When Render gives you a URL such as `https://aeris-api.onrender.com`, set:

```text
ALLOWED_ORIGINS=https://your-demo.vercel.app
```

You can temporarily use the final web-host URL after the web deployment. Add
local development origins too if needed, separated by commas.

## 2. Publish the Vite app

Import this repository into Vercel (or use the Vercel CLI), selecting `web` as
the Root Directory. Set these settings:

| Setting | Value |
| --- | --- |
| Framework preset | Vite |
| Build command | `npm run build` |
| Output directory | `dist` |
| Environment variable | `VITE_API_BASE_URL=https://aeris-api.onrender.com` |

Deploy. Vercel provides a public `*.vercel.app` URL that can be sent to anyone.
Update the API's `ALLOWED_ORIGINS` with that exact origin, then redeploy the
API once.

## Local check

Run the API from the repository root:

```bash
PYTHONPATH=. uvicorn snapshot_api.app.main:api --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd web
npm run dev
```

Open `http://localhost:5173`.

`VITE_API_BASE_URL` is embedded during the Vite build. Change it in the host's
environment settings and redeploy the web app whenever the API URL changes.
