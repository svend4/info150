# triage4-drive web UI

React + TypeScript + Vite single-page dashboard. Backend:
`triage4_drive.ui.dashboard_api`.

## Run

```bash
# Backend (terminal 1, from triage4-drive/)
pip install -e ".[ui]"
uvicorn triage4_drive.ui.dashboard_api:app --reload

# Frontend (terminal 2, from triage4-drive/web_ui/)
npm install && npm run dev   # http://localhost:5173
```

Note: drive channel scores are RISK scores (higher = worse), inverted
relative to the rest of the catalog.
