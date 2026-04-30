# triage4-fish web UI

Single-page React + TypeScript + Vite dashboard for the
**triage4-fish** sibling — aquaculture pen welfare. Talks to the
FastAPI backend at `triage4_fish.ui.dashboard_api`, served on
`http://127.0.0.1:8000` by default.

This file is **copy-paste ready** for both Linux/macOS and Windows
PowerShell. Pick the section that matches your machine.

---

## 0. Prerequisites

| Tool       | Version | Check with             | Where to get                                                |
|------------|---------|------------------------|-------------------------------------------------------------|
| Python     | ≥ 3.11  | `python --version`     | https://www.python.org/downloads/                           |
| Node.js    | ≥ 18    | `node --version`       | https://nodejs.org/ (LTS) or `winget install OpenJS.NodeJS.LTS` |
| npm        | ≥ 9     | `npm --version`        | bundled with Node                                           |
| git        | any     | `git --version`        | https://git-scm.com/                                        |

You will need **two terminal windows** open at the same time — one
for the FastAPI backend, one for the React/Vite frontend.

---

## 1. Quickstart — Linux / macOS

### Terminal 1 — backend (FastAPI on :8000)

```bash
# Clone (only first time)
git clone https://github.com/svend4/info150.git

# Create + activate a venv at the monorepo root
cd info150
python -m venv .venv
source .venv/bin/activate

# Install the sibling with the [ui] extra (adds fastapi + uvicorn + httpx)
cd triage4-fish
pip install -e ".[ui]"

# Run the FastAPI dashboard. Leave this terminal running.
uvicorn triage4_fish.ui.dashboard_api:app --reload
```

After the last command you should see:

```
INFO:     Will watch for changes in these directories: ['.../triage4-fish']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

Smoke-check the API in a third terminal (or a browser):

```bash
curl http://127.0.0.1:8000/health
# {"service":"triage4-fish","version":"0.1.0",...}
```

### Terminal 2 — frontend (Vite on :5173)

Open a **new terminal**. The venv does NOT need to be active here —
this terminal only runs npm.

```bash
cd info150/triage4-fish/web_ui

# Install JS dependencies (first time only — ~30 seconds)
npm install

# Run the dev server. Leave this terminal running.
npm run dev
```

You should see:

```
  VITE v5.x.x  ready in 350 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

Open `http://localhost:5173` in your browser. The dashboard loads:
- header with farm ID and pen counts
- three colored cards per welfare level (steady / watch / urgent)
- left list of pens — click any one
- right detail panel: 5 channel bars + alerts
- "Re-seed demo" button regenerates synthetic data

---

## 2. Quickstart — Windows PowerShell

PowerShell 5.x (the default on Windows 10/11) does **not** support
`&&`. Each command goes on its own line. PowerShell 7+ accepts `&&`
but the recipe below works in both.

### Terminal 1 — backend (FastAPI on :8000)

```powershell
# Clone (only first time)
git clone https://github.com/svend4/info150.git

# Create + activate a venv at the monorepo root
cd info150
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# If activation is blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Install the sibling with the [ui] extra
cd triage4-fish
pip install -e ".[ui]"

# Run the FastAPI dashboard. Leave this PS window running.
python -m uvicorn triage4_fish.ui.dashboard_api:app --reload
```

Smoke-check the API in a third PS window:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health | Select-Object -ExpandProperty Content
```

### Terminal 2 — frontend (Vite on :5173)

Open a **new PowerShell window**.

```powershell
cd C:\Users\<your-username>\info150\triage4-fish\web_ui
# (Replace <your-username> with your actual Windows user folder.)

# Install JS dependencies (first time only)
npm install

# Run the dev server. Leave this PS window running.
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 3. What's actually running

Two processes:

| Process | Port | What it does                                         |
|---------|------|------------------------------------------------------|
| uvicorn | 8000 | FastAPI app — JSON API for the React UI              |
| vite    | 5173 | React/TS dev server — proxies API calls to :8000     |

The Vite dev server is configured (`vite.config.ts`) to proxy these
paths to the FastAPI backend so CORS never fires:
`/health`, `/report`, `/pens`, `/alerts`, `/demo`, `/export.html`.

---

## 4. Stopping

In each terminal, press **`Ctrl+C`**. Both processes shut down
cleanly. To leave the venv: `deactivate` (works in both bash and PS).

---

## 5. Re-seed the demo data

While both servers are running:

- Click **"Re-seed demo"** in the UI header, **or**
- Hit the API directly:

  ```bash
  # Linux / macOS
  curl -X POST http://127.0.0.1:8000/demo/reload
  ```

  ```powershell
  # Windows PowerShell
  Invoke-WebRequest -Method POST http://127.0.0.1:8000/demo/reload
  ```

Both produce a fresh `PenReport`. Numbers change deterministically
with the synthetic generator's seed.

---

## 6. Production build (optional)

Build a static bundle into `web_ui/dist/`:

```bash
# Linux / macOS — from triage4-fish/web_ui/
npm run build
npm run preview   # serves dist/ on http://localhost:4173 for sanity check
```

```powershell
# Windows PowerShell — from triage4-fish\web_ui\
npm run build
npm run preview
```

---

## 7. Offline HTML snapshot — no UI needed

If you only want to look at the data in a browser without running
React/Vite, the FastAPI backend ships a self-contained HTML at
`/export.html`:

```bash
curl http://127.0.0.1:8000/export.html > fish.html
open fish.html        # macOS
xdg-open fish.html    # Linux
```

```powershell
Invoke-WebRequest http://127.0.0.1:8000/export.html -OutFile fish.html
start fish.html       # Windows
```

The exported HTML works fully offline — no JavaScript, no fetch
calls, just the rendered pen table and alert list.

---

## 8. Update / uninstall

### Update to the latest version

Run from the monorepo root (two levels up from this folder).

```bash
# Linux / macOS
cd ../..                          # to info150/
source .venv/bin/activate
git pull origin main
cd triage4-fish
pip install -e ".[ui]"             # in case pyproject.toml changed
cd web_ui
npm install                        # in case package.json changed
```

```powershell
# Windows PowerShell
cd ..\..
.\.venv\Scripts\Activate.ps1
git pull origin main
cd triage4-fish
pip install -e ".[ui]"
cd web_ui
npm install
```

Then restart `uvicorn` (Ctrl+C in its terminal, re-run) and
`npm run dev` to pick up backend / frontend changes.

### Uninstall just this sibling

```bash
# Linux / macOS — from this directory
cd ..                              # to triage4-fish/
make clean
pip uninstall -y triage4-fish
rm -rf web_ui/node_modules web_ui/dist
```

```powershell
# Windows PowerShell
cd ..
pip uninstall -y triage4-fish
Remove-Item -Recurse -Force web_ui\node_modules, web_ui\dist -ErrorAction SilentlyContinue
```

The folder `triage4-fish/` itself stays on disk. To wipe it
completely, see the **full monorepo uninstall** recipe.

### Full monorepo uninstall

For the comprehensive recipe (all 17 packages, venv, Docker, every
`node_modules/`, every cache) — Linux/macOS AND Windows PowerShell
variants — see
[`../../INSTALL.md#uninstall--remove-a-package-or-the-whole-monorepo`](../../INSTALL.md#uninstall--remove-a-package-or-the-whole-monorepo).

---

## 9. Troubleshooting

| Symptom                                          | Fix                                                                                  |
|--------------------------------------------------|--------------------------------------------------------------------------------------|
| `ModuleNotFoundError: No module named 'fastapi'` | You forgot `[ui]`. Run `pip install -e ".[ui]"` (note the double quotes on Windows). |
| `ModuleNotFoundError: No module named 'biocore'` | Install biocore first: from monorepo root run `pip install -e biocore/`.             |
| `npm: command not found` / `npm не распознан`    | Install Node.js 18+ and reopen the terminal so PATH is refreshed.                    |
| `port 8000 already in use`                       | Another uvicorn is running. Stop it (or use `--port 8001` + update `TRIAGE4_FISH_API_TARGET`). |
| `port 5173 already in use`                       | Another Vite is running. Stop it (or `npm run dev -- --port 5174`).                  |
| Browser shows "Error talking to API"             | The FastAPI backend on 8000 isn't running. Start Terminal 1 first.                   |
| `cannot be loaded because running scripts is disabled` (PS) | Run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.          |
| `Token "&&" ist in dieser Version kein gültiges …` (PS 5.x) | Use `;` instead of `&&`, or upgrade to PowerShell 7+.                     |
| `cd : ...info150\info150\... not found`          | You ran the cd from inside `info150` already. Drop the prefix: `cd triage4-fish`.    |
| Backend reloads on save but UI doesn't           | Vite hot-reload watches `web_ui/src/`. Make sure you edited a file under `src/`.     |

---

## 10. File map

```
web_ui/
├── package.json        # npm dependencies (react, react-dom, vite, ts)
├── tsconfig.json       # TypeScript strict mode
├── vite.config.ts      # Dev-server proxy → :8000
├── index.html          # entry HTML
├── README.md           # this file
├── .gitignore          # node_modules/, dist/
└── src/
    ├── main.tsx        # React entry
    ├── App.tsx         # the dashboard
    ├── api.ts          # fetch wrappers
    ├── types.ts        # TypeScript interfaces matching FastAPI shapes
    └── styles.css      # global CSS
```

The matching FastAPI dashboard lives at
`triage4_fish/ui/dashboard_api.py` (one level up).

---

## 11. See also

- `../README.md` — sibling-level overview (engine, signatures, demo)
- `../../DEMOS.md` — full catalogue of every package's UI
- `../../INSTALL.md` — monorepo-level install guide
