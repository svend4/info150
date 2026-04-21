# triage4 — Public API

Это **кураторский список публичного API**. Все остальные символы
(частные helper-функции, имена с префиксом `_`, re-export'ы, оставленные
ради upstream-совместимости) — внутренние и могут измениться без
предупреждения.

Цель документа — дать intellectual handle на 104-модульную базу:
что импортировать в 90% случаев, а куда нырять только при необходимости.

## Core data model

```python
from triage4.core import (
    CasualtyNode,         # главный объект: пострадавший в триадже
    CasualtySignature,    # все измеренные сигналы + визуальная видимость
    TraumaHypothesis,     # одна гипотеза о травме
    GeoPose,              # 2D/3D поза (xyz + yaw + frame)
    TriagePriority,       # immediate / delayed / minimal / expectant / unknown
    CasualtyStatus,       # detected / tracked / assessed / handed_off / lost
    HypothesisType,       # каталог видов травм
    PlatformType,         # uav / ugv / quadruped
)
```

## Signatures

```python
from triage4.signatures import (
    BreathingSignatureExtractor,   # 1D motion curve → breathing descriptor
    BleedingSignatureExtractor,    # visual + thermal + pooling → bleeding
    PerfusionSignatureExtractor,   # skin-color curve → perfusion drop
    ThermalSignatureExtractor,     # thermal patch → hotspot + asymmetry
    PostureSignatureExtractor,     # body-region polygons → collapse + asymmetry
    FractalMotionAnalyzer,         # fractal / CSS / chain-code descriptors
    SignatureRegistry,             # runtime register + batch extract
)
```

Радар-подсигнатуры (когда нужен многомерный профиль):

```python
from triage4.signatures.radar import (
    HeptagramSignature, build_heptagram_signature,        # 7 осей
    OctagramSignature, build_octagram_signature,          # 8 осей + 3D
    HexSignature, build_hex_signature,                    # 6-bit Q6 fingerprint
)
```

## Perception

```python
from triage4.perception import BodyRegionPolygonizer
```

## Graphs

```python
from triage4.graph import CasualtyGraph, MissionGraph, GraphUpdateService
```

## Triage reasoning

```python
from triage4.triage_reasoning import (
    RapidTriageEngine,       # sig → (priority, score, reasons)
    TraumaAssessmentEngine,  # sig → [TraumaHypothesis]
    ExplainabilityBuilder,   # node → human-readable summary
    UncertaintyModel,        # propagate per-channel quality
    VitalsEstimator,         # FFT-based HR / RR
)
```

## Autonomy

```python
from triage4.autonomy import (
    RevisitPolicy,
    HumanHandoffService,
    TaskAllocator,
    plan_robot_route,         # BFS на mission edges
    bfs_path,
)
```

## Evaluation (DARPA gates)

```python
from triage4.evaluation import (
    evaluate_gate1, Gate1Report,    # find + locate
    evaluate_gate2, Gate2Report,    # rapid triage classification
    evaluate_gate3, Gate3Report,    # multi-label trauma
    evaluate_gate4, Gate4Report,    # HR / RR accuracy
    evaluate_hmt_lane, HMTReport, HMTEvent,
)
```

## Platform bridges

```python
from triage4.integrations import (
    PlatformBridge, PlatformTelemetry, BridgeUnavailable,
    LoopbackWebSocketBridge,
    LoopbackMAVLinkBridge,
    LoopbackROS2Bridge,
    LoopbackSpotBridge,
    # factories that lazy-import the real SDK:
    build_fastapi_websocket_bridge,
    build_pymavlink_bridge,
    build_rclpy_bridge,
    build_bosdyn_bridge,
)
```

## UI / simulation

```python
from triage4.ui.dashboard_api import app    # FastAPI app
from triage4.ui.html_export import render_html
from triage4.sim import SensorDegradationSimulator, DegradationConfig
```

---

## Реже используемый API (deep layers)

Это не private, но в обычных use-case'ах обычно не нужно — тянуть только
когда надо собирать свой собственный pipeline.

### K3-матрица 2.x — semantic reasoning

```python
from triage4.semantic import EvidenceToken, build_evidence_tokens
from triage4.state_graph import (
    BodyStateGraph, EvidenceMemory,
    check_casualty_graph_consistency,
)
from triage4.triage_temporal import TemporalMemory, DeteriorationModel
```

### K3-матрица 3.x — mission / world

```python
from triage4.tactical_scene import TacticalSceneBuilder
from triage4.mission_coordination import TaskQueue, AssignmentEngine
from triage4.world_replay import TimelineStore, ReplayEngine
```

### Matching (низкоуровневые дистанции и fusion)

```python
from triage4.matching import (
    # distances
    dtw_distance, dtw_distance_mirror, rotation_dtw,
    hausdorff_distance, chamfer_distance, frechet_approx,
    shape_similarity, shape_distances,
    descriptor_distance, descriptor_similarity,
    # fusion
    ScoreVector, CombinedScore, weighted_combine,
    # shape descriptors
    CurveDescriptor, describe_curve,
    FragmentGeometry, compute_geometry_from_contour, match_geometry,
    # orientation
    OrientProfile, compute_orient_profile, match_orient_pair,
    # ranking
    CandidatePair, rank_pairs, top_k,
    # affine
    estimate_affine, apply_affine_pts, match_points_affine,
    # registry
    register, get_matcher, compute_scores,
)
```

### Scoring (верхний уровень — над matching)

```python
from triage4.scoring import (
    # threshold selection
    select_threshold, select_otsu_threshold, select_f1_threshold,
    ThresholdConfig,
    # rank fusion
    reciprocal_rank_fusion, borda_count, fuse_rankings,
    # evidence aggregation
    EvidenceConfig, EvidenceScore, aggregate_evidence,
    # structured ranking pipeline
    RankConfig, RankResult, rank_pairs_detailed,
    # global multi-matrix ranking
    global_rank, RankingConfig,
    # pair filtering
    filter_pairs, FilterConfig,
    # match evaluation (precision / recall / F-β)
    evaluate_match, MatchEval, aggregate_eval,
    # consistency reports
    ConsistencyReport, ConsistencyIssue, run_consistency_check,
)
```

---

## Какие имена **внутренние**

- Всё с префиксом `_` внутри любого модуля.
- Файлы, помеченные как verbatim-port upstream без новой публичной
  обёртки над ними (например, `triage4.matching.boundary_matcher.*`
  использует 4-sides bbox concept, уместный только для документов;
  для триажа лучше вызывать `triage4.matching.shape_similarity`).
- Re-export'ы под именами с префиксом `Filter*`, `Global*`, `Hex*` и
  т.п. — сделаны ради избежания name clash'ей между portированными
  модулями, а не потому что это рекомендованное публичное имя.

---

## Гарантии стабильности

- **Стабильно:** все имена из секций Core / Signatures / Perception /
  Graphs / Triage reasoning / Autonomy / Evaluation / Platform bridges.
- **Может измениться:** секция «Реже используемый API» — это чаще
  upstream-ported surface, и если upstream меняет имена, наш re-export
  тоже двинется.
- **Не API:** всё, что в `tests/` или `examples/`. Пользоваться
  полезно, но для production-импорта не предназначено.
