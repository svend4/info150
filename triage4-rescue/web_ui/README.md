# triage4-rescue web UI

React + TypeScript + Vite single-page dashboard for the triage4-rescue
sibling. Talks to `triage4_rescue.ui.dashboard_api` (FastAPI) on
`http://127.0.0.1:8000` by default.

## Run

```bash
# 1. Backend (in one terminal, from triage4-rescue/)
pip install -e ".[ui]"
uvicorn triage4_rescue.ui.dashboard_api:app --reload

# 2. Frontend (in another terminal, from triage4-rescue/web_ui/)
npm install
npm run dev   # http://localhost:5173
```

`npm run dev` proxies `/health`, `/incident`, `/casualties`,
`/alerts`, `/demo`, `/export.html` to the backend so the dev
server runs on the same origin and CORS never fires.

## Build

```bash
npm run build       # output: dist/
npm run preview     # serves dist/ on http://localhost:4173
```

## What it shows

- Casualty count + per-tag totals (immediate / delayed / minor / deceased)
- List of casualties (click for detail)
- Per-casualty reasoning + responder cues
- Re-seed button to regenerate the synthetic incident

This is a sibling-scale dashboard — single-page, ~250 LOC of TS/TSX.
For the multi-page flagship dashboard see `../../triage4/web_ui/`.
