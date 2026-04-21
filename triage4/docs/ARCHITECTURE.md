# triage4 — Architecture

## 1. Назначение

`triage4` — слоистая decision-support архитектура для stand-off triage:
дрон/UGV/quadruped + stand-off sensors → perception → signatures → reasoning
→ graph → autonomy / handoff / UI.

## 2. Базовый pipeline

```text
sensing → perception → signatures → reasoning → graph → autonomy → ui/handoff
```

## 3. Слои

### 3.1 Core (`triage4/core`)

- `enums.py` — `TriagePriority`, `CasualtyStatus`, `HypothesisType`, `PlatformType`
- `models.py` — `GeoPose`, `CasualtySignature`, `TraumaHypothesis`, `CasualtyNode`

### 3.2 Perception (`triage4/perception`)

- `person_detector.py` — интерфейс детектора
- `pose_estimator.py` — интерфейс позы
- `body_regions.py` — тангра́мная декомпозиция тела в полигоны

### 3.3 Signatures (`triage4/signatures`)

- `breathing_signature.py` — дыхательный прокси
- `bleeding_signature.py` — bleeding-прокси
- `perfusion_signature.py` — перфузия кожи
- `fractal_motion.py` — motion-complexity proxy (meta2-inspired)
- `registry.py` — реестр экстракторов

### 3.4 Reasoning (`triage4/triage_reasoning`)

- `rapid_triage.py` — быстрый triage с объяснениями
- `trauma_assessment.py` — trauma-гипотезы
- `explainability.py` — summary для операторов

### 3.5 Graph (`triage4/graph`)

- `casualty_graph.py`
- `mission_graph.py`
- `updates.py`

### 3.6 Autonomy (`triage4/autonomy`)

- `revisit.py`
- `human_handoff.py`
- `task_allocator.py`

### 3.7 Integrations (`triage4/integrations`)

- `meta2_adapter.py` — обёртка для fractal-движка `meta2`
- `infom_adapter.py` — экспорт casualty-graph в infom-формате
- `in4n_adapter.py` — экспорт сцены для in4n-вьювера

### 3.8 UI (`triage4/ui`)

- `dashboard_api.py` — FastAPI дашборд
- `seed.py` — демо-данные

### 3.9 Simulation (`triage4/sim`)

- `casualty_profiles.py` — профили сигналов по priority hint
- `synthetic_benchmark.py` — демо-запуск

## 4. K3-матрица 3×3

Фрактальная декомпозиция: три уровня × три режима.

| Уровень | `.1` Linear/Signal | `.2` Structural/Relational | `.3` Dynamic/Spatiotemporal |
|---|---|---|---|
| **K3-1 Micro Perception** | Temporal Signature (`signatures/`) | Spatial Body Map (`perception/body_regions.py`) | Dynamic Skeletal Graph (roadmap) |
| **K3-2 Semantic Reasoning** | Evidence Semantics (`semantic/`) | Relational Body-State (`state_graph/`) | Temporal Triage (`triage_temporal/`) |
| **K3-3 Mission / World** | Tactical Scene (`tactical_scene/`) | Mission Coordination (`mission_coordination/`) | Strategic Replay (`world_replay/`) |

## 5. Ключевые сущности

### `CasualtyNode`

Центральный объект. Живёт сквозь весь pipeline и накапливает сигнатуры,
гипотезы и приоритет.

### `CasualtySignature`

Агрегированное описание сигналов: breathing curve, chest motion FD,
perfusion drop, bleeding score, posture, body region polygons.

### `TraumaHypothesis`

`kind`, `score`, `evidence`, `explanation` — всегда с объяснением, это
требование decision-support подхода.

### `MissionGraph`

Назначения robot↔casualty, medic↔casualty, очередь revisit, unresolved
sectors.

## 6. Мэппинг на DARPA gates

Смотри `docs/darpa_mapping.md`.

## 7. Не-цели

Проект **не** ставит диагноз и **не** заменяет медика. Это decision-support
и mission-support stack.
