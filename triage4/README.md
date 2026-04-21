# triage4

> Simulation-first autonomous stand-off triage stack.

`triage4` — интеграционный research-стек под задачу автономного дистанционного
triage'а (DARPA Triage Challenge Event 3 и аналогичные сценарии полевой
медицины). Объединяет три концептуальные линии из черновиков проекта:

- **`meta2`** → структурные дескрипторы, фракталы, полигоны, matching / fusion;
- **`infom`** → граф знаний, память, reasoning;
- **`in4n`** → 3D / динамическая визуализация, живой граф, агентная навигация.

## Статус

**Roadmap Phases 1–8 закрыты.** 104 Python-модуля, 380 тестов (все зелёные),
ruff + mypy чистые, 0 импортов upstream-репозиториев во время загрузки.

| Phase | Статус | Что |
|---|---|---|
| 1 | ✅ | Scaffold + core dataclasses |
| 2 | ✅ | Simulation-first perception MVP |
| 3 | ✅ | Signatures + rapid triage |
| 4 | ✅ | Casualty / mission graph + dashboard |
| 5 | ✅ | Autonomy (revisit, handoff, task allocator) |
| 6 | ✅ | K3 fractal matrix (partial diagonals) |
| 6.5 | ✅ | Upstream integration — 24 meta2 + 4 infom + 3 in4n verbatim ports |
| 7 | ✅ | Multimodal (thermal, posture, uncertainty, vitals, degradation) + 5 DARPA gate evaluators |
| 8 | ✅ | Platform bridges — ROS2 / MAVLink / Spot / WebSocket (все с loopback-симуляторами) |

См. [`docs/ROADMAP.md`](docs/ROADMAP.md) и [`CHANGELOG.md`](CHANGELOG.md) для
полной истории.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### End-to-end synthetic benchmark

Показывает полный pipeline (perception → signatures → triage → graph →
autonomy → bridge → evaluation через 5 DARPA gates) на 8 фикстурных пациентах:

```bash
python examples/full_pipeline_benchmark.py
```

Пример вывода:

```
Gate 1 — find & locate
   precision=1.000  recall=1.000  F1=1.000
   mean error = 0.72 m  max error = 1.57 m
Gate 2 — rapid triage
   accuracy=1.000  macro_f1=0.600  critical_miss_rate=0.000
Gate 3 — trauma hypotheses
   macro_f1=0.600  micro_f1=0.571  mean_hamming=0.333
Gate 4 — vitals accuracy
   HR  n= 8  MAE=1.9  RMSE=2.1  hit_rate@±10bpm=1.00
   RR  n= 8  MAE=1.9  RMSE=2.0  hit_rate@±3bpm=1.00
HMT lane
   events=8  mean_time=57.5 s  agreement=1.000  override=0.000
```

### FastAPI dashboard

```bash
uvicorn triage4.ui.dashboard_api:app --reload
```

| Endpoint | Что отдаёт |
|---|---|
| `GET /health` | состояние + число узлов графа |
| `GET /casualties` | полный список пострадавших |
| `GET /casualties/{id}` | карточка пациента |
| `GET /casualties/{id}/explain` | triage-решение с объяснениями |
| `GET /casualties/{id}/handoff` | payload для передачи медику |
| `GET /graph` | `CasualtyGraph` как JSON |
| `GET /map` | тактическая карта |
| `GET /replay` | кадры replay-timeline |
| `GET /tasks` | рекомендованная очередь вмешательств |
| `GET /export.html` | self-contained HTML-снимок (работает offline) |

### Web UI

```bash
cd web_ui
npm install
npm run dev
```

### Тесты

```bash
pytest -q                                   # 380 tests
pytest tests/test_end_to_end.py             # integration only
ruff check triage4 tests
mypy --ignore-missing-imports triage4
```

## Структура

```text
triage4/
├── pyproject.toml
├── configs/sim.yaml
├── README.md  CHANGELOG.md
├── docs/                       # ANALYSIS / ARCHITECTURE / ROADMAP / API / darpa_mapping
├── third_party/                # upstream attribution таблица
├── LICENSES/                   # meta2 и сопутствующие MIT notices
├── examples/                   # full_pipeline_benchmark + рецепты
├── tests/                      # 380 unit + 2 end-to-end
├── web_ui/                     # React + Vite dashboard
└── triage4/                    # сам пакет (104 файла)
    ├── core/                   # dataclasses, enums
    ├── perception/             # body_regions, detector, pose
    ├── signatures/             # breathing / bleeding / perfusion / thermal /
    │   │                       # posture / fractal_motion
    │   ├── fractal/            # box_counting, divider, CSS, chain_code
    │   └── radar/              # heptagram, octagram, hexsig (Q6)
    ├── matching/               # DTW, rotation_dtw, affine, boundary,
    │                           # curve_descriptor, orient, score_combiner, …
    ├── scoring/                # threshold_selector, rank_fusion,
    │                           # evidence_aggregator, pair_ranker, pair_filter,
    │                           # match_evaluator, global_ranker,
    │                           # consistency_checker
    ├── triage_reasoning/       # rapid_triage / trauma / explainability /
    │                           # score_fusion / uncertainty / vitals_estimation
    ├── graph/                  # casualty / mission / updates
    ├── state_graph/            # body state graph, evidence memory, consistency
    ├── semantic/               # evidence tokens (K3-2.1)
    ├── triage_temporal/        # temporal memory, deterioration
    ├── tactical_scene/         # K3-3.1 map projection
    ├── mission_coordination/   # K3-3.2 task_queue + assignment_engine
    ├── world_replay/           # K3-3.3 timeline store + replay
    ├── autonomy/               # revisit / human_handoff / task_allocator /
    │                           # route_planner (BFS)
    ├── evaluation/             # 5 DARPA gate evaluators
    │                           # gate1_find_locate, gate2_rapid_triage,
    │                           # gate3_trauma, gate4_vitals, hmt_lane
    ├── integrations/           # meta2/infom/in4n adapters +
    │                           # PlatformBridge + ROS2/MAVLink/Spot/WebSocket
    ├── sim/                    # casualty_profiles, synthetic_benchmark,
    │                           # sensor_degradation
    └── ui/                     # FastAPI dashboard + html_export + seed
```

## Документация

- [`CHANGELOG.md`](CHANGELOG.md) — история коммитов по фазам
- [`docs/API.md`](docs/API.md) — публичный API triage4
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — архитектура и K3-матрица
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — план развития
- [`docs/ANALYSIS.md`](docs/ANALYSIS.md) — разбор исходных черновиков
- [`docs/darpa_mapping.md`](docs/darpa_mapping.md) — карта модулей → DARPA gates
- [`third_party/ATTRIBUTION.md`](third_party/ATTRIBUTION.md) — upstream lineage
- [`LICENSES/README.md`](LICENSES/README.md) — licensing posture

## Disclaimer

Репозиторий предназначен для **исследований, симуляций и прототипирования
decision-support систем**. Это **не сертифицированное медицинское устройство**
и не должен использоваться как самостоятельный источник клинических решений.

## License

MIT. Для адаптированных модулей сохранены upstream MIT-notices в
[`LICENSES/`](LICENSES/).
