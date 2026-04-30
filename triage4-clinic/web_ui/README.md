# triage4-clinic web UI

React + TypeScript + Vite single-page dashboard. Backend:
`triage4_clinic.ui.dashboard_api`.

## Run

```bash
# Backend (terminal 1, from triage4-clinic/)
pip install -e ".[ui]"
uvicorn triage4_clinic.ui.dashboard_api:app --reload

# Frontend (terminal 2, from triage4-clinic/web_ui/)
npm install && npm run dev   # http://localhost:5173
```
