# triage4-bird web UI

React + TypeScript + Vite single-page dashboard. Backend:
`triage4_bird.ui.dashboard_api`.

## Run

```bash
# Backend (terminal 1, from triage4-bird/)
pip install -e ".[ui]"
uvicorn triage4_bird.ui.dashboard_api:app --reload

# Frontend (terminal 2, from triage4-bird/web_ui/)
npm install && npm run dev   # http://localhost:5173
```
