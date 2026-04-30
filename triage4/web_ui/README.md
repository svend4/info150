# triage4 web UI (flagship)

Multi-page React + TypeScript + Vite dashboard for the **flagship
`triage4`** project — DARPA Triage Challenge stand-off triage stack.
This UI is significantly larger than the sibling-level dashboards
(11 pages, ~7500 LOC of TS/TSX, semantic-zoom map, replay timeline)
because the flagship doubles as a research showcase.

Talks to the FastAPI backend at `triage4.ui.dashboard_api`, served on
`http://127.0.0.1:8000` by default.

This file is **copy-paste ready** for both Linux/macOS and Windows
PowerShell.

---

## 0. Prerequisites

| Tool       | Version | Check with             | Where to get                                                |
|------------|---------|------------------------|-------------------------------------------------------------|
| Python     | ≥ 3.11  | `python --version`     | https://www.python.org/downloads/                           |
| Node.js    | ≥ 18    | `node --version`       | https://nodejs.org/ (LTS) or `winget install OpenJS.NodeJS.LTS` |
| npm        | ≥ 9     | `npm --version`        | bundled with Node                                           |
| git        | any     | `git --version`        | https://git-scm.com/                                        |

You will need **two terminal windows** at the same time — one for
the FastAPI backend, one for the React/Vite frontend.

The flagship's `make install-dev` already pulls `httpx` (the FastAPI
test-client dependency) so the API is fully runnable after a single
install. No separate `[ui]` extra needed at the flagship layer.

---

## 1. Quickstart — Linux / macOS

### Terminal 1 — backend (FastAPI on :8000)

```bash
git clone https://github.com/svend4/info150.git
cd info150
python -m venv .venv
source .venv/bin/activate
cd triage4

# Install flagship + dev tooling (includes fastapi, uvicorn, httpx)
make install-dev
# Equivalent without make:
#   pip install -e ".[dev]"
#   pip install ruff mypy httpx

# Run the FastAPI dashboard
uvicorn triage4.ui.dashboard_api:app --reload
```

Smoke-check the API:

```bash
curl http://127.0.0.1:8000/health
# {"ok":true,"casualty_count":...}
curl http://127.0.0.1:8000/casualties | head -c 200
```

### Terminal 2 — frontend (Vite on :5173)

Open a **new terminal**.

```bash
cd info150/triage4/web_ui
npm install
npm run dev
```

Open `http://localhost:5173`. The flagship UI loads with a top
navigation bar — eleven tabs:

| Tab            | What it shows                                              |
|----------------|------------------------------------------------------------|
| Home           | landing + status                                           |
| Casualties     | full casualty list, click for explainability               |
| Mission        | mission status + resource handoffs                         |
| Forecast       | per-casualty + mission-level forecast                      |
| Scorecard      | DARPA Gate 1–4 evaluator scorecard                         |
| Tasks          | recommended intervention queue                             |
| Sensing        | active-sensing ranked recommendations                      |
| Map            | tactical-scene map projection (semantic-zoom)              |
| Replay         | mission-timeline frame-by-frame replay                     |
| Graph          | full `CasualtyGraph` JSON view                             |
| Metrics        | Prometheus `/metrics` formatted                            |

Hotkeys `1`–`9` jump tabs.

---

## 2. Quickstart — Windows PowerShell

### Terminal 1 — backend

```powershell
git clone https://github.com/svend4/info150.git
cd info150
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# If activation is blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
cd triage4

# Install flagship + dev tooling
pip install -e ".[dev]"
pip install ruff mypy httpx

# Run the FastAPI dashboard
python -m uvicorn triage4.ui.dashboard_api:app --reload
```

Smoke-check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health | Select-Object -ExpandProperty Content
```

### Terminal 2 — frontend

Open a **new PowerShell window**.

```powershell
cd C:\Users\<your-username>\info150\triage4\web_ui
npm install
npm run dev
```

Open `http://localhost:5173`.

---

## 3. What's running

| Process | Port | What it does                                                |
|---------|------|-------------------------------------------------------------|
| uvicorn | 8000 | FastAPI app — JSON API + Prometheus `/metrics`              |
| vite    | 5173 | React/TS dev server with proxies into the FastAPI backend   |

Vite dev-server proxy targets (configured in `vite.config.ts`):
`/health`, `/metrics`, `/casualties` (+ all sub-routes), `/graph`,
`/map`, `/replay`, `/tasks`, `/export.html`, `/mission`, `/forecast`,
`/evaluation`, `/overview`, `/sensing`. Override the backend host
via `TRIAGE4_API_TARGET` env var.

---

## 4. Stopping

`Ctrl+C` in each terminal. Then `deactivate` to leave the venv.

---

## 5. Production build

```bash
# Linux / macOS — from triage4/web_ui/
npm run build
npm run preview          # http://localhost:4173 (sanity check)
```

```powershell
# Windows PowerShell — from triage4\web_ui\
npm run build
npm run preview
```

The bundle goes to `web_ui/dist/`. Serve with any HTTP server.

---

## 6. Offline HTML snapshot — no React needed

The FastAPI backend ships a self-contained HTML at `/export.html` —
single-file dashboard, works fully offline:

```bash
# Linux / macOS
curl http://127.0.0.1:8000/export.html > triage4.html
open triage4.html      # macOS
xdg-open triage4.html  # Linux
```

```powershell
# Windows PowerShell
Invoke-WebRequest http://127.0.0.1:8000/export.html -OutFile triage4.html
start triage4.html
```

---

## 7. Docker alternative (no Python or Node on the host)

The flagship ships a Docker image + compose stack:

```bash
# from info150/triage4/
make docker-compose-up           # docker compose up -d
curl http://localhost:8000/health
make docker-compose-down         # docker compose down
```

The Docker image is API-only (no React UI inside). For a TLS
reverse-proxy front-end, use the `edge` profile:

```bash
docker compose --profile edge up -d
```

See `../docs/DEPLOYMENT.md` for the three deployment profiles
(container / systemd / edge).

---

## 8. Troubleshooting

| Symptom                                          | Fix                                                                                  |
|--------------------------------------------------|--------------------------------------------------------------------------------------|
| `ModuleNotFoundError: No module named 'httpx'` (test collection) | `pip install httpx` — the flagship's [dev] extra doesn't include it; `make install-dev` does. |
| `npm: command not found`                         | Install Node.js 18+ and reopen the terminal.                                         |
| `port 8000 already in use`                       | Stop the other uvicorn (or use `--port 8001` + set `TRIAGE4_API_TARGET=http://127.0.0.1:8001`). |
| `port 5173 already in use`                       | `npm run dev -- --port 5174`.                                                        |
| Browser shows a blank screen                     | Check the browser console + the Vite terminal. Most often: backend not running on 8000. |
| `cannot be loaded because running scripts is disabled` (PS) | Run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.          |
| `Token "&&" ist in dieser Version kein gültiges …` (PS 5.x) | Use `;` instead of `&&`, or upgrade to PowerShell 7+.                     |
| `cd : ...info150\info150\... not found`          | You ran the cd from inside `info150` already. Drop the prefix: `cd triage4`.         |
| `webcam_triage_demo.py` fails to find OpenCV     | Optional dep: `pip install opencv-python` (only needed for the real-camera demo).   |

---

## 9. File map

```
triage4/web_ui/
├── package.json           # react, react-dom, vite, typescript
├── tsconfig.json          # strict TS
├── vite.config.ts         # dev-server proxy → :8000 (12 path prefixes)
├── package-lock.json
├── index.html             # entry HTML
├── README.md              # this file
└── src/
    ├── main.tsx           # React entry (mounts ToastProvider)
    ├── App.tsx            # 11-tab top-level layout
    ├── types.ts           # cross-page TS interfaces
    ├── api/               # fetch wrappers per backend route group
    ├── components/        # layout, map, info panel, semantic zoom
    ├── hooks/             # useHotkeys, useQuerySync
    ├── pages/             # one .tsx per top-level tab
    ├── state/             # ToastContext + cross-page state
    ├── styles/            # global.css
    ├── util/              # priority, filters, format, export helpers
    └── vite-env.d.ts
```

Backend code: `../triage4/ui/dashboard_api.py` (one level up).

---

## 10. Sibling Web UIs

The 14 catalogue siblings each ship their own minimal sibling-level
Web UI under `<sibling>/web_ui/`. They follow the same React+Vite+TS
pattern as this flagship UI but are single-page and ~250-300 LOC
(vs ~7500 here). See [`../../DEMOS.md`](../../DEMOS.md) for the
sibling catalogue.

---

## 11. See also

- `../README.md` — flagship overview (DARPA Gates, K3 matrix)
- `../docs/STATUS.md` — honest project status
- `../docs/ARCHITECTURE.md` — K3 matrix + fractal recursion
- `../docs/DEPLOYMENT.md` — container / systemd / edge profiles
- `../../DEMOS.md` — every package's UI in the monorepo
- `../../INSTALL.md` — monorepo install guide
