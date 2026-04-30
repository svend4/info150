# triage4-farm web UI

React + TypeScript + Vite single-page dashboard for the triage4-farm
sibling. Talks to `triage4_farm.ui.dashboard_api` (FastAPI).

## Run

```bash
# Backend (terminal 1, from triage4-farm/)
pip install -e ".[ui]"
uvicorn triage4_farm.ui.dashboard_api:app --reload

# Frontend (terminal 2, from triage4-farm/web_ui/)
npm install && npm run dev   # http://localhost:5173
```
