# DARPA Triage Challenge Event 3 — модули triage4

## Gate 1: Find and locate

Модули:

- `triage4/perception/person_detector.py`
- `triage4/perception/pose_estimator.py`
- `triage4/graph/casualty_graph.py`
- roadmap: `triage4/autonomy/search_planner.py`

## Gate 2: Rapid triage

Модули:

- `triage4/signatures/breathing_signature.py`
- `triage4/signatures/bleeding_signature.py`
- `triage4/signatures/perfusion_signature.py`
- `triage4/triage_reasoning/rapid_triage.py`
- `triage4/graph/casualty_graph.py`

## Gate 3: Trauma assessment

Модули:

- `triage4/triage_reasoning/trauma_assessment.py`
- `triage4/triage_reasoning/explainability.py`
- `triage4/semantic/evidence_tokens.py`
- `triage4/state_graph/body_state_graph.py`

## Gate 4: Accurate vitals (optional)

Модули:

- `triage4/signatures/breathing_signature.py`
- `triage4/signatures/perfusion_signature.py`
- `triage4/signatures/fractal_motion.py`
- roadmap: `triage4/triage_reasoning/vitals_estimation.py`

## Human-machine teaming lane

Модули:

- `triage4/graph/mission_graph.py`
- `triage4/autonomy/human_handoff.py`
- `triage4/autonomy/task_allocator.py`
- `triage4/mission_coordination/task_queue.py`
- `triage4/mission_coordination/assignment_engine.py`
- `triage4/ui/dashboard_api.py`
- `web_ui/src/App.tsx`
