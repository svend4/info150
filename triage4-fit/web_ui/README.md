# triage4-fit web UI

React + TypeScript + Vite single-page dashboard. Backend:
`triage4_fit.ui.dashboard_api`.

## Run

```bash
# Backend (terminal 1, from triage4-fit/)
pip install -e ".[ui]"
uvicorn triage4_fit.ui.dashboard_api:app --reload

# Frontend (terminal 2, from triage4-fit/web_ui/)
npm install && npm run dev   # http://localhost:5173
```
