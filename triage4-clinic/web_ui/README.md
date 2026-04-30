# triage4-clinic web UI

Single-page React + TypeScript + Vite dashboard for the
**triage4-clinic** sibling — telemedicine pre-triage pre-screening
(per-submission cardiac, respiratory, acoustic, postural channels +
clinician alerts). Talks to the FastAPI backend at
`triage4_clinic.ui.dashboard_api` on `http://127.0.0.1:8000` by
default.

This file is **copy-paste ready** for both Linux/macOS and Windows
PowerShell.

**Note:** triage4-clinic uses a `recommendation` literal of
`self_care / schedule / urgent_review`.

---

## 0. Prerequisites

| Tool       | Version | Check with             | Where to get                                                |
|------------|---------|------------------------|-------------------------------------------------------------|
| Python     | ≥ 3.11  | `python --version`     | https://www.python.org/downloads/                           |
| Node.js    | ≥ 18    | `node --version`       | https://nodejs.org/ (LTS)                                   |
| npm        | ≥ 9     | `npm --version`        | bundled with Node                                           |
| git        | any     | `git --version`        | https://git-scm.com/                                        |

You will need **two terminal windows** at the same time.

---

## 1. Quickstart — Linux / macOS

### Terminal 1 — backend (FastAPI on :8000)

```bash
git clone https://github.com/svend4/info150.git
cd info150
python -m venv .venv
source .venv/bin/activate
cd triage4-clinic
pip install -e ".[ui]"
uvicorn triage4_clinic.ui.dashboard_api:app --reload
```

Smoke-check:

```bash
curl http://127.0.0.1:8000/health
# {"service":"triage4-clinic","version":"0.1.0","submission_count":...}
```

### Terminal 2 — frontend (Vite on :5173)

Open a **new terminal**.

```bash
cd info150/triage4-clinic/web_ui
npm install
npm run dev
```

Open `http://localhost:5173`. The dashboard shows:
- header with submission count
- three cards: self-care / schedule / urgent review
- left list of patients
- right detail: 4 channel bars (cardiac, respiratory, acoustic, postural) + clinician alerts + symptoms
- Re-seed button

---

## 2. Quickstart — Windows PowerShell

### Terminal 1 — backend

```powershell
git clone https://github.com/svend4/info150.git
cd info150
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# If activation is blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
cd triage4-clinic
pip install -e ".[ui]"
python -m uvicorn triage4_clinic.ui.dashboard_api:app --reload
```

### Terminal 2 — frontend

Open a **new PowerShell window**.

```powershell
cd C:\Users\<your-username>\info150\triage4-clinic\web_ui
npm install
npm run dev
```

Open `http://localhost:5173`.

---

## 3. What's running

| Process | Port | What it does                                         |
|---------|------|------------------------------------------------------|
| uvicorn | 8000 | FastAPI app — JSON API                               |
| vite    | 5173 | React/TS dev server — proxies to :8000               |

Vite proxies: `/health`, `/report`, `/submissions`, `/alerts`,
`/demo`, `/export.html`.

---

## 4. Stopping

`Ctrl+C` in each terminal. Then `deactivate`.

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

---

## 6. Production build (optional)

```bash
npm run build
npm run preview
```

---

## 7. Offline HTML snapshot

```bash
curl http://127.0.0.1:8000/export.html > clinic.html
open clinic.html        # macOS
xdg-open clinic.html    # Linux
```

```powershell
Invoke-WebRequest http://127.0.0.1:8000/export.html -OutFile clinic.html
start clinic.html
```

---

## 8. Update / uninstall

### Update to the latest version

Run from the monorepo root (two levels up from this folder).

```bash
# Linux / macOS
cd ../..                          # to info150/
source .venv/bin/activate
git pull origin main
cd triage4-clinic
pip install -e ".[ui]"             # in case pyproject.toml changed
cd web_ui
npm install                        # in case package.json changed
```

```powershell
# Windows PowerShell
cd ..\..
.\.venv\Scripts\Activate.ps1
git pull origin main
cd triage4-clinic
pip install -e ".[ui]"
cd web_ui
npm install
```

Then restart `uvicorn` (Ctrl+C in its terminal, re-run) and
`npm run dev` to pick up backend / frontend changes.

### Uninstall just this sibling

```bash
# Linux / macOS — from this directory
cd ..                              # to triage4-clinic/
make clean
pip uninstall -y triage4-clinic
rm -rf web_ui/node_modules web_ui/dist
```

```powershell
# Windows PowerShell
cd ..
pip uninstall -y triage4-clinic
Remove-Item -Recurse -Force web_ui\node_modules, web_ui\dist -ErrorAction SilentlyContinue
```

The folder `triage4-clinic/` itself stays on disk. To wipe it
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
| `ModuleNotFoundError: No module named 'fastapi'` | Run `pip install -e ".[ui]"`.                                                        |
| `npm: command not found`                         | Install Node.js 18+ and reopen the terminal.                                         |
| `port 8000 already in use`                       | Stop the other uvicorn or use `--port 8001` + `TRIAGE4_CLINIC_API_TARGET=...`.       |
| `port 5173 already in use`                       | `npm run dev -- --port 5174`.                                                        |
| "Error talking to API"                           | Backend on 8000 isn't running. Start Terminal 1 first.                               |
| PS 5.x `&&` parser error                         | Use `;` or upgrade to PowerShell 7+.                                                 |
| PS execution policy block                        | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.                               |

---

## 10. File map

```
web_ui/
├── package.json
├── tsconfig.json
├── vite.config.ts      # dev-server proxy → :8000
├── index.html
├── README.md
├── .gitignore
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── api.ts
    ├── types.ts
    └── styles.css
```

Backend code: `../triage4_clinic/ui/dashboard_api.py`.

---

## 11. See also

- `../README.md` — sibling overview (ClinicalPreTriageEngine, decision-support framing)
- `../../DEMOS.md` — full UI catalogue
- `../../INSTALL.md` — monorepo install guide
