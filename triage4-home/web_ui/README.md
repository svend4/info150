# triage4-home web UI

React + TypeScript + Vite single-page dashboard. Backend:
`triage4_home.ui.dashboard_api`.

## Run

```bash
# Backend (terminal 1, from triage4-home/)
pip install -e ".[ui]"
uvicorn triage4_home.ui.dashboard_api:app --reload

# Frontend (terminal 2, from triage4-home/web_ui/)
npm install && npm run dev   # http://localhost:5173
```
