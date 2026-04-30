# triage4

> Simulation-first autonomous stand-off triage stack.

`triage4` — интеграционный research-стек под задачу автономного дистанционного
triage'а (DARPA Triage Challenge Event 3 и аналогичные сценарии полевой
медицины). Объединяет три концептуальные линии из черновиков проекта:

- **`meta2`** → структурные дескрипторы, фракталы, полигоны, matching / fusion;
- **`infom`** → граф знаний, память, reasoning;
- **`in4n`** → 3D / динамическая визуализация, живой граф, агентная навигация.

## Статус

**Roadmap Phases 1–9e + 10-prep + 12 + 13-prep + Levels A/B/C закрыты.**
130 Python-модулей, **759 тестов** (все зелёные), ruff + mypy + claims-lint
чистые, 0 импортов upstream-репозиториев / внешних SDK во время загрузки.

Честный анализ плюсов / минусов / того что ещё открыто — в
[`docs/STATUS.md`](docs/STATUS.md).

| Phase | Статус | Что |
|---|---|---|
| 1–6 | ✅ | Scaffold, core, perception MVP, signatures, triage, graphs, autonomy, K3 matrix |
| 6.5 | ✅ | Upstream integration — 24 meta2 + 4 infom + 3 in4n verbatim ports |
| 7 | ✅ | Multimodal (thermal / posture / uncertainty / vitals / degradation) + 5 DARPA gate evaluators |
| 8 | ✅ | Platform bridges — ROS2 / MAVLink / Spot / WebSocket (все с loopback-симуляторами) |
| 9a | ✅ | Eulerian stand-off vitals, information-gain active sensing, Larrey baseline |
| 9b | ✅ | YOLO adapter, PhysioNet adapter, 70-case realistic dataset, grid-search calibrator, Larrey-gap closed |
| 9c | ✅ | Bayesian patient twin, counterfactual replay, entropy handoff, CRDT denied-comms, acoustic signature, LLM grounding |
| 9d | ✅ | Consolidation — expanded benchmark, demo scripts, API docs, one-pager |
| 9e | ✅ | Steganographic markers, C.elegans classifier, fractal mission-as-casualty |
| 10-prep | ✅ | `BridgeHealth` + `PlatformBridge` contract tests + per-platform wiring guide |
| 12 | ✅ | Regulatory awareness (REGULATORY + SAFETY_CASE + RISK_REGISTER) |
| 13-prep | ✅ | Dockerfile + systemd unit + nginx template + 3 deployment profiles |
| Level A | ✅ | claims-lint (CLAIM-001 closed) · mutation testing (CI-002 closed) · `MultiPlatformManager` · Prometheus `/metrics` |
| Level B | ✅ | Makefile · CONTRIBUTING · SBOM generator · hypothesis property tests (+ marker_codec bug fix) |
| Level C | ✅ | stress benchmark · multi-platform / calibration / replay демо · CALIBRATION + EXPLAINABILITY docs |

**Все 9 клеток K3-матрицы реализованы.** Включая три бывших stub'а
(`1.3` skeletal graph, `2.2` conflict resolver, `3.3` forecast layer) —
закрыты в текущем коммите.

Открытые пункты требуют внешних ресурсов:

- **Phase 10 proper** — живое железо (UAV / quadruped / сенсорная цепь).
- **Phase 11** — клинический партнёр + IRB approval.
- **Phase 13 proper** — заказчик / production site.

См. [`docs/ROADMAP.md`](docs/ROADMAP.md) и [`CHANGELOG.md`](CHANGELOG.md) для
полной истории.

## Быстрый старт

С чистой машины — скачать, установить, прогнать тесты:

```bash
# 1. Скачать монорепо
git clone https://github.com/svend4/info150.git
cd info150/triage4

# 2. Виртуальное окружение
python -m venv .venv
source .venv/bin/activate

# 3. Установить + проверить + прогнать бенчмарк
make install-dev        # либо: pip install -e '.[dev]' && pip install ruff mypy httpx
make qa                 # ruff + mypy + claims-lint + pytest (~3 s)
make benchmark          # полный pipeline на 8 фикстурных пациентах
```

Если уже скачали репо ранее — пропустите шаг 1, начните с `cd info150/triage4`.

Полная инструкция по установке всех 17 пакетов (биокор, портал,
14 сиблингов) — в [корневом README](../README.md#installation-from-scratch).

Все основные задачи — через `make help`. Типичные:

```bash
make test               # pytest -q
make demo-crdt          # denied-comms CRDT sync, 3 медика
make demo-marker        # оффлайн-марким + rollback на tampered/expired
make demo-multi         # multi-platform orchestrator: UAV + Spot + ROS2
make demo-calibration   # grid-search calibration walkthrough
make demo-replay        # mission timeline replay
make stress             # scaling benchmark (10 / 100 / 500 casualties)
make docker-build       # slim image < 200 MB
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

### Docker / docker-compose

Слим-образ (< 200 MB) с FastAPI dashboard внутри. Production-ready
hardening: read-only rootfs, dropped caps, no-new-privileges, healthcheck.

```bash
# Простейшая сборка + запуск
make docker-build       # docker build -t triage4:0.1.0 .
make docker-run         # docker run --rm -p 8000:8000 triage4:0.1.0
curl http://localhost:8000/health
```

Через `docker-compose.yml` (восстанавливается после рестарта, healthcheck,
hardening настройки):

```bash
make docker-compose-up      # docker compose up -d
curl http://localhost:8000/health
make docker-compose-down    # docker compose down
```

С TLS-фронтендом (nginx reverse-proxy на 8443) — поднимается через
профиль `edge`. Перед запуском подложите валидные TLS-сертификаты в
`configs/` и заполните bearer-auth в `configs/nginx.conf`:

```bash
docker compose --profile edge up -d
```

Конфигурация runtime — через переменные окружения:
`TRIAGE4_CONFIG=/app/configs/production.yaml`,
`TRIAGE4_LOG_LEVEL=info`. Полные профили деплоя (container / systemd /
edge) — в [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

### Тесты

```bash
make test                                   # 595 tests, ~3 s
pytest tests/test_end_to_end.py             # integration only
make lint mypy claims-lint                  # три линта (или make qa — все вместе)
make mutation-quick                         # mutation testing (opt-in, ~1 min)
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

Основная:
- [`docs/STATUS.md`](docs/STATUS.md) — честный статус: плюсы, минусы, что ещё открыто
- [`CHANGELOG.md`](CHANGELOG.md) — история коммитов по фазам
- [`docs/API.md`](docs/API.md) — публичный API triage4
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — архитектура и K3-матрица
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — план развития
- [`docs/ONE_PAGER.md`](docs/ONE_PAGER.md) — grant-ready one-pager
- [`docs/PHASE_9_SUMMARY.md`](docs/PHASE_9_SUMMARY.md) — рекап Phase 9
- [`docs/FURTHER_READING.md`](docs/FURTHER_READING.md) — bibliography

Регуляторика и безопасность:
- [`docs/REGULATORY.md`](docs/REGULATORY.md) — SaMD / IEC 62304 / FDA / EU MDR landscape (non-binding)
- [`docs/SAFETY_CASE.md`](docs/SAFETY_CASE.md) — GSN-style safety argument
- [`docs/RISK_REGISTER.md`](docs/RISK_REGISTER.md) — ISO 14971-style реестр
- [`docs/EXPLAINABILITY.md`](docs/EXPLAINABILITY.md) — три слоя объяснений + LLM grounding
- [`docs/CALIBRATION.md`](docs/CALIBRATION.md) — tuning fusion weights + thresholds против dataset

Интеграция и деплой:
- [`docs/HARDWARE_INTEGRATION.md`](docs/HARDWARE_INTEGRATION.md) — per-platform wiring
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — container / systemd / edge профили
- [`docs/MUTATION_TESTING.md`](docs/MUTATION_TESTING.md) — mutmut scope + usage

Процесс и происхождение:
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — conventions для PR / тестов / claims-lint
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
