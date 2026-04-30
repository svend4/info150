# triage4-crowd web UI

React + TypeScript + Vite single-page dashboard for the triage4-crowd
sibling. Talks to `triage4_crowd.ui.dashboard_api` (FastAPI).

## Run

```bash
# Backend (terminal 1, from triage4-crowd/)
pip install -e ".[ui]"
uvicorn triage4_crowd.ui.dashboard_api:app --reload

# Frontend (terminal 2, from triage4-crowd/web_ui/)
npm install && npm run dev   # http://localhost:5173
```
