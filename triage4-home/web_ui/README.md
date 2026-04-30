# triage4-home web UI

Single-page React + TypeScript + Vite dashboard for the
**triage4-home** sibling — elderly home / in-home monitoring
(per-window fall risk, activity alignment, mobility trend). Talks to
the FastAPI backend at `triage4_home.ui.dashboard_api` on
`http://127.0.0.1:8000` by default.

This file is **copy-paste ready** for both Linux/macOS and Windows
PowerShell.

**Note:** triage4-home uses an `alert_level` literal of
`ok / check_in / urgent` (slightly different from the rest of the
catalog's `ok / watch / urgent`).

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
cd triage4-home
pip install -e ".[ui]"
uvicorn triage4_home.ui.dashboard_api:app --reload
```

Smoke-check:

```bash
curl http://127.0.0.1:8000/health
# {"service":"triage4-home","version":"0.1.0","residence_id":"DEMO_RESIDENCE",...}
```

### Terminal 2 — frontend (Vite on :5173)

Open a **new terminal**.

```bash
cd info150/triage4-home/web_ui
npm install
npm run dev
```

Open `http://localhost:5173`. The dashboard shows:
- header with residence ID + window count + alert count
- three cards: ok / check-in / urgent
- left list of windows
- right detail: 3 channel bars (fall risk, activity alignment, mobility trend) + caregiver alerts
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
cd triage4-home
pip install -e ".[ui]"
python -m uvicorn triage4_home.ui.dashboard_api:app --reload
```

### Terminal 2 — frontend

Open a **new PowerShell window**.

```powershell
cd C:\Users\<your-username>\info150\triage4-home\web_ui
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

Vite proxies: `/health`, `/report`, `/windows`, `/alerts`, `/demo`,
`/export.html`.

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
curl http://127.0.0.1:8000/export.html > home.html
open home.html        # macOS
xdg-open home.html    # Linux
```

```powershell
Invoke-WebRequest http://127.0.0.1:8000/export.html -OutFile home.html
start home.html
```

---

## 8. Troubleshooting

| Symptom                                          | Fix                                                                                  |
|--------------------------------------------------|--------------------------------------------------------------------------------------|
| `ModuleNotFoundError: No module named 'fastapi'` | Run `pip install -e ".[ui]"`.                                                        |
| `npm: command not found`                         | Install Node.js 18+ and reopen the terminal.                                         |
| `port 8000 already in use`                       | Stop the other uvicorn or use `--port 8001` + `TRIAGE4_HOME_API_TARGET=...`.         |
| `port 5173 already in use`                       | `npm run dev -- --port 5174`.                                                        |
| "Error talking to API"                           | Backend on 8000 isn't running. Start Terminal 1 first.                               |
| PS 5.x `&&` parser error                         | Use `;` or upgrade to PowerShell 7+.                                                 |
| PS execution policy block                        | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.                               |

---

## 9. File map

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

Backend code: `../triage4_home/ui/dashboard_api.py`.

---

## 10. See also

- `../README.md` — sibling overview (HomeMonitoringEngine, baseline-aware)
- `../../DEMOS.md` — full UI catalogue
- `../../INSTALL.md` — monorepo install guide
