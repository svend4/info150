# triage4-site web UI

React + TypeScript + Vite single-page dashboard for the triage4-site
sibling. Talks to `triage4_site.ui.dashboard_api` (FastAPI).

## Run

```bash
# Backend (terminal 1, from triage4-site/)
pip install -e ".[ui]"
uvicorn triage4_site.ui.dashboard_api:app --reload

# Frontend (terminal 2, from triage4-site/web_ui/)
npm install && npm run dev   # http://localhost:5173
```
