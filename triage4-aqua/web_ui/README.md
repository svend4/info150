# triage4-aqua web UI

React + TypeScript + Vite single-page dashboard for the triage4-aqua
sibling. Talks to `triage4_aqua.ui.dashboard_api` (FastAPI) on
`http://127.0.0.1:8000` by default.

## Run

```bash
# 1. Backend (terminal 1, from triage4-aqua/)
pip install -e ".[ui]"
uvicorn triage4_aqua.ui.dashboard_api:app --reload

# 2. Frontend (terminal 2, from triage4-aqua/web_ui/)
npm install && npm run dev   # http://localhost:5173
```
