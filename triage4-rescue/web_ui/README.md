# triage4-rescue web UI

Single-page React + TypeScript + Vite dashboard for the
**triage4-rescue** sibling — civilian mass-casualty triage support
(START / JumpSTART). Talks to the FastAPI backend at
`triage4_rescue.ui.dashboard_api`, served on `http://127.0.0.1:8000`
by default.

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

You will need **two terminal windows** open at the same time — one
for the FastAPI backend, one for the React/Vite frontend.

---

## 1. Quickstart — Linux / macOS

### Terminal 1 — backend (FastAPI on :8000)

```bash
git clone https://github.com/svend4/info150.git
cd info150
python -m venv .venv
source .venv/bin/activate
cd triage4-rescue
pip install -e ".[ui]"
uvicorn triage4_rescue.ui.dashboard_api:app --reload
```

Smoke-check the API:

```bash
curl http://127.0.0.1:8000/health
# {"service":"triage4-rescue","version":"0.1.0","incident_id":"DEMO_INCIDENT",...}
```

### Terminal 2 — frontend (Vite on :5173)

Open a **new terminal**.

```bash
cd info150/triage4-rescue/web_ui
npm install
npm run dev
```

Open `http://localhost:5173`. The dashboard loads:
- header with incident ID + casualty count
- four colored cards by START tag (immediate / delayed / minor / deceased)
- left list of casualties — click any one
- right detail panel: reasoning + age group + responder cues
- "Re-seed demo" button regenerates the synthetic incident

---

## 2. Quickstart — Windows PowerShell

### Terminal 1 — backend

```powershell
git clone https://github.com/svend4/info150.git
cd info150
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# If activation is blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
cd triage4-rescue
pip install -e ".[ui]"
python -m uvicorn triage4_rescue.ui.dashboard_api:app --reload
```

Smoke-check:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health | Select-Object -ExpandProperty Content
```

### Terminal 2 — frontend

Open a **new PowerShell window**.

```powershell
cd C:\Users\<your-username>\info150\triage4-rescue\web_ui
npm install
npm run dev
```

Open `http://localhost:5173`.

---

## 3. What's running

| Process | Port | What it does                                         |
|---------|------|------------------------------------------------------|
| uvicorn | 8000 | FastAPI app — JSON API for the React UI              |
| vite    | 5173 | React/TS dev server — proxies API calls to :8000     |

Vite proxies these paths to the backend (CORS never fires):
`/health`, `/incident`, `/casualties`, `/alerts`, `/demo`, `/export.html`.

---

## 4. Stopping

`Ctrl+C` in each terminal. Then `deactivate` to leave the venv.

---

## 5. Re-seed demo data

```bash
# Linux / macOS
curl -X POST http://127.0.0.1:8000/demo/reload
```

```powershell
# Windows PowerShell
Invoke-WebRequest -Method POST http://127.0.0.1:8000/demo/reload
```

Or just press the **"Re-seed demo"** button in the UI.

---

## 6. Production build (optional)

```bash
# Linux / macOS — from triage4-rescue/web_ui/
npm run build
npm run preview   # http://localhost:4173
```

```powershell
# Windows PowerShell — from triage4-rescue\web_ui\
npm run build
npm run preview
```

---

## 7. Offline HTML snapshot — no UI needed

```bash
curl http://127.0.0.1:8000/export.html > rescue.html
open rescue.html      # macOS
xdg-open rescue.html  # Linux
```

```powershell
Invoke-WebRequest http://127.0.0.1:8000/export.html -OutFile rescue.html
start rescue.html
```

The exported HTML works fully offline — table of casualties + tags +
reasoning, no JS.

---

## 8. Update / uninstall

### Update to the latest version

Run from the monorepo root (two levels up from this folder).

```bash
# Linux / macOS
cd ../..                          # to info150/
source .venv/bin/activate
git pull origin main
cd triage4-rescue
pip install -e ".[ui]"             # in case pyproject.toml changed
cd web_ui
npm install                        # in case package.json changed
```

```powershell
# Windows PowerShell
cd ..\..
.\.venv\Scripts\Activate.ps1
git pull origin main
cd triage4-rescue
pip install -e ".[ui]"
cd web_ui
npm install
```

Then restart `uvicorn` (Ctrl+C in its terminal, re-run) and
`npm run dev` to pick up backend / frontend changes.

### Uninstall just this sibling

```bash
# Linux / macOS — from this directory
cd ..                              # to triage4-rescue/
make clean
pip uninstall -y triage4-rescue
rm -rf web_ui/node_modules web_ui/dist
```

```powershell
# Windows PowerShell
cd ..
pip uninstall -y triage4-rescue
Remove-Item -Recurse -Force web_ui\node_modules, web_ui\dist -ErrorAction SilentlyContinue
```

The folder `triage4-rescue/` itself stays on disk. To wipe it
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
| `ModuleNotFoundError: No module named 'fastapi'` | You forgot `[ui]`. Run `pip install -e ".[ui]"`.                                     |
| `npm: command not found` / `npm не распознан`    | Install Node.js 18+ and reopen the terminal so PATH is refreshed.                    |
| `port 8000 already in use`                       | Stop the other uvicorn (or use `--port 8001` + update `TRIAGE4_RESCUE_API_TARGET`).  |
| `port 5173 already in use`                       | Stop the other Vite (or `npm run dev -- --port 5174`).                               |
| Browser shows "Error talking to API"             | The FastAPI backend on 8000 isn't running. Start Terminal 1 first.                   |
| `cannot be loaded because running scripts is disabled` (PS) | Run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.          |
| `Token "&&" ist in dieser Version kein gültiges …` (PS 5.x) | Use `;` instead of `&&`, or upgrade to PowerShell 7+.                     |
| `cd : ...info150\info150\... not found`          | You ran the cd from inside `info150` already. Drop the prefix: `cd triage4-rescue`.  |

---

## 10. File map

```
web_ui/
├── package.json        # react, react-dom, vite, typescript
├── tsconfig.json       # strict mode
├── vite.config.ts      # dev-server proxy → :8000
├── index.html
├── README.md           # this file
├── .gitignore
└── src/
    ├── main.tsx        # React entry
    ├── App.tsx         # dispatcher dashboard
    ├── api.ts          # fetch wrappers
    ├── types.ts        # TS interfaces matching FastAPI shapes
    └── styles.css
```

---

## 11. See also

- `../README.md` — sibling overview (START + JumpSTART, multiuser pilot)
- `../../DEMOS.md` — full UI catalogue across the monorepo
- `../../INSTALL.md` — monorepo install guide
- `../../V13_REUSE_MAP.md` — context for the rescue multiuser pilot
