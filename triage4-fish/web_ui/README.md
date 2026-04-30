# triage4-fish web UI

React + TypeScript + Vite single-page dashboard for the triage4-fish
sibling. Talks to `triage4_fish.ui.dashboard_api` (FastAPI) on
`http://127.0.0.1:8000` by default.

## Run

```bash
# 1. Backend (in one terminal, from triage4-fish/)
pip install -e ".[ui]"
uvicorn triage4_fish.ui.dashboard_api:app --reload

# 2. Frontend (in another terminal, from triage4-fish/web_ui/)
npm install
npm run dev   # http://localhost:5173
```

## Build

```bash
npm run build       # output: dist/
npm run preview     # serves dist/ on http://localhost:4173
```

## What it shows

- Per-level totals (steady / watch / urgent)
- List of pens (click for detail)
- Per-pen 5-channel breakdown with score bars
- Per-pen alerts with claims-guarded text
- Re-seed button to regenerate the synthetic farm

This is a sibling-scale dashboard — single-page, ~280 LOC of TS/TSX.
