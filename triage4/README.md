# triage4

> Simulation-first autonomous stand-off triage stack.
> MVP-каркас, собранный из черновиков `Branch · Branch · Branch · Обзор проекта svend4_meta2.*`.

`triage4` — это интеграционный репозиторий, объединяющий три концептуальные линии
(описанные в черновиках):

- **`meta2`** → структурные дескрипторы, фракталы, полигоны, matching / fusion;
- **`infom`** → граф знаний, память, reasoning;
- **`in4n`** → 3D / динамическая визуализация, живой граф, агентная навигация.

Назначение пакета — превратить эти три линии в минимальный рабочий
stand-off triage stack для UAV / UGV / quadruped-платформ.

## Быстрый старт

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Запустить API

```bash
uvicorn triage4.ui.dashboard_api:app --reload
```

Доступные эндпоинты:

- `GET /health`
- `GET /casualties`
- `GET /casualties/{id}`
- `GET /casualties/{id}/explain`
- `GET /casualties/{id}/handoff`
- `GET /graph`
- `GET /map`
- `GET /replay`
- `GET /tasks`

### Запустить synthetic benchmark

```bash
python -m triage4.sim.synthetic_benchmark
```

### Запустить тесты

```bash
pip install -e '.[dev]'
pytest
```

### Запустить Web UI

```bash
cd web_ui
npm install
npm run dev
```

## Структура

```text
triage4/
├── pyproject.toml
├── configs/sim.yaml
├── triage4/
│   ├── core/                  # модели, enum'ы
│   ├── graph/                 # casualty_graph / mission_graph / updates
│   ├── perception/            # person_detector / pose_estimator / body_regions
│   ├── signatures/            # breathing / bleeding / perfusion / fractal_motion
│   ├── triage_reasoning/      # rapid_triage / trauma_assessment / explainability
│   ├── autonomy/              # revisit / human_handoff / task_allocator
│   ├── semantic/              # K3-2.1 evidence tokens
│   ├── state_graph/           # K3-2.2 body state graph
│   ├── triage_temporal/       # K3-2.3 temporal memory / deterioration
│   ├── tactical_scene/        # K3-3.1 map projection
│   ├── mission_coordination/  # K3-3.2 task_queue / assignment_engine
│   ├── world_replay/          # K3-3.3 timeline_store / replay_engine
│   ├── integrations/          # meta2 / infom / in4n адаптеры
│   ├── sim/                   # synthetic_benchmark / casualty_profiles
│   └── ui/                    # FastAPI dashboard + seed
├── web_ui/                    # React + Vite дашборд
├── tests/
└── docs/
```

## Документация

- [`docs/ANALYSIS.md`](docs/ANALYSIS.md) — оценка черновиков (плюсы / минусы)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — архитектура и K3-матрица
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — план развития
- [`docs/darpa_mapping.md`](docs/darpa_mapping.md) — карта модулей → DARPA gates

## Disclaimer

Репозиторий предназначен для **исследований, симуляций и прототипирования
decision-support систем**. Это не сертифицированное медицинское устройство.

## License

MIT
