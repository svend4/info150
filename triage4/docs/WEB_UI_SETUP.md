# Web UI — dev setup

How to run the React dashboard against the FastAPI backend in a
two-terminal local setup. Covers the Vite dev proxy, the relative
`API_BASE`, and the CORS-aware backend defaults.

## 0. Prerequisites

- **Backend side:** `pip install -e '.[dev]'` from `triage4/`.
- **Frontend side:** Node.js ≥ 20 (`node --version` to check).

## 1. Architecture

```
        browser: http://localhost:5173/
                 │
                 │  GET /casualties, /map, /replay
                 ▼
        Vite dev server (5173)
                 │
                 │  proxy (vite.config.ts)
                 ▼
        FastAPI (uvicorn) on 127.0.0.1:8000
```

Two processes, one browser tab. The Vite proxy forwards every
backend path prefix (`/health`, `/metrics`, `/casualties` +
sub-routes, `/graph`, `/map`, `/replay`, `/tasks`, `/export.html`,
`/mission`, `/forecast`, `/evaluation`, `/overview`, `/sensing`) to
the FastAPI server, so the browser sees only the frontend origin
(`localhost:5173`) — **no cross-origin, no CORS preflight**. The
list lives in `web_ui/vite.config.ts` — when a new backend path is
added, extend `BACKEND_PATHS` there too or the Vite dev server will
return 404 for the new route.

## 2. Run both processes

**Terminal A — backend.** From `triage4/`:

```bash
# macOS / Linux
source .venv/bin/activate
uvicorn triage4.ui.dashboard_api:app --reload

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
uvicorn triage4.ui.dashboard_api:app --reload
```

Expected:

```
INFO: Uvicorn running on http://127.0.0.1:8000
INFO: Application startup complete.
```

Verify in a browser:

- `http://127.0.0.1:8000/health` → `{"ok":true,"nodes":8}`
- `http://127.0.0.1:8000/casualties` → JSON array of 8 casualties

**Terminal B — frontend.** From `triage4/web_ui/`:

```bash
npm install          # first run only
npm run dev
```

Expected:

```
Local:   http://localhost:5173/
```

Open it in the browser. The sidebar should show **8 casualties**,
colour-coded by priority. The `Map` and `Replay` tabs should
render non-empty data.

## 3. Troubleshooting

### Sidebar is empty

F12 → Network → reload. Look at the `/casualties` request.

| Status | Cause | Fix |
|---|---|---|
| **net::ERR_CONNECTION_REFUSED** | Backend not running | Start Terminal A (section 2). |
| **502 / proxy error** | Vite can't reach backend | Confirm backend is on `127.0.0.1:8000`; if it's on a different port / host, set `TRIAGE4_API_TARGET=http://host:port` before `npm run dev`. |
| **CORS error** | Only possible if you bypass the Vite proxy | See section 4 — you probably edited `API_BASE` or removed the proxy. |
| **200 OK but blank UI** | Response shape mismatch | Check the payload matches `src/types.ts`. |

### Backend starts from the wrong directory

Uvicorn's `Will watch for changes in these directories:` line must
point at `info150/triage4`. If it points at your home directory
or elsewhere, quit uvicorn and `cd` into `triage4/` before
re-running the command. Otherwise `--reload` watches the wrong
tree, and any code change won't trigger a reload.

### Port 8000 or 5173 already in use

```bash
# backend on 8001 instead
uvicorn triage4.ui.dashboard_api:app --reload --port 8001

# frontend picks up the new backend via env var
TRIAGE4_API_TARGET=http://127.0.0.1:8001 npm run dev
```

Windows PowerShell syntax:

```powershell
$env:TRIAGE4_API_TARGET = "http://127.0.0.1:8001"; npm run dev
```

### Building for production

```bash
cd web_ui
npm run build    # outputs dist/
```

The built bundle expects the backend to be reachable at the same
origin. When hosting behind a reverse proxy (nginx, Caddy, etc.),
route `/health`, `/casualties`, etc. to the FastAPI instance. See
`configs/nginx.conf` for a reference template.

If the frontend must run on a different host than the backend in
production, set `VITE_API_BASE=https://api.example.com` at build
time:

```bash
VITE_API_BASE=https://api.example.com npm run build
```

## 4. What changed vs. the previous setup

Historical footgun: the Vite config had no proxy, the React app
hard-coded `http://127.0.0.1:8000`, and the FastAPI middleware had
`allow_origins=["*"]` **together with** `allow_credentials=True`.
Browsers reject that CORS combination by spec — the preflight
never passes. Symptom: frontend renders but the sidebar stays
empty, Network tab shows no data.

Current setup avoids the failure mode entirely:

- `vite.config.ts` proxies backend paths on `:5173` → `:8000`.
- `App.tsx` uses a relative `API_BASE` (default `""`) — overridable
  with `VITE_API_BASE` at build time.
- `dashboard_api.py` CORS block uses an explicit allowlist
  (`http://localhost:5173`, `http://127.0.0.1:5173`, plus the
  `:4173` vite-preview variants) and **does not** claim
  `allow_credentials`.

So even callers that bypass the Vite proxy (native `fetch` from a
dev console, curl with `--origin`, Electron shell) still reach
the backend without a CORS rejection — they just can't send
cookies, which triage4 has no use for in its current mode.

## 5. Non-goals

- No authentication. The dashboard is single-operator,
  single-mission. A bearer-token layer would belong in
  `dashboard_api.py` before any deployment beyond localhost — see
  `docs/DEPLOYMENT.md §3` for the secret-env-var slots.
- No session persistence. The backend rebuilds the casualty graph
  on every startup from `ui/seed.py`.
- No real-time push. Polling the endpoints on tab-switch is
  enough for the 8-casualty reference scene. A WebSocket channel
  via `LoopbackWebSocketBridge` is available for future live-feed
  use cases.
