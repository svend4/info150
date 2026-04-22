# triage4 — Explainability

Every triage decision in triage4 is explainable by construction,
not because an external tool was stapled on. Three layers of
explanation travel with every output:

1. **Reasons list** — the heuristic facts that fired
   (`mortal-sign override`, `immediate casualties dominate the
   queue`, ...).
2. **Per-channel confidence** — a [0, 1] quality score for each
   sensor input.
3. **Natural-language summary** — optional, grounded on the facts
   above; never invented.

This document describes how the three layers are produced, how an
LLM can be attached without compromising regulatory framing, and
what the operator can expect to see on the dashboard.

## 1. Three layers, one contract

### Layer 1 — reasons

`RapidTriageEngine.infer_priority(sig)` returns
`(priority, score, reasons)` where `reasons` is a list of short
strings. Current generators:

- `score_fusion.priority_from_score` — adds
  `"mortal-sign override"` whenever a single channel trips its
  `MortalThresholds` value, regardless of fused score.
- Engine internals add per-channel contributions like
  `"high bleeding score (0.85)"`.
- `mission_coordination/mission_triage` generates mission-level
  reasons such as `"medic team saturated"` or
  `"mission window nearly exhausted"`.

**Invariant:** every non-trivial decision carries at least one
reason. Tests assert this — see `tests/test_score_fusion.py` and
`tests/test_phase9e.py::test_classify_mission_escalates_under_pressure`.

### Layer 2 — per-channel confidence

`UncertaintyModel().from_signature(sig, base_score=score)` returns
an `UncertaintyReport` with:

- `per_channel_confidence: dict[str, float]` —
  `breathing_quality`, `perfusion_quality`, `bleeding_confidence`,
  `thermal_quality` (and a few others depending on what the
  signature carried).
- `overall_confidence: float` — aggregated, monotone in the
  channels.
- `adjusted_score: float` — `base_score` discounted by confidence.

The `raw_features` dict on `CasualtySignature` is the entry point
for quality flags. Sensor drivers set them; the reasoner reads
them. If a channel is missing, the UncertaintyModel returns
`0.0` confidence on it — **low confidence never silently
upgrades**.

### Layer 3 — natural-language summary

Two builders produce text:

- **`ExplainabilityBuilder`** — deterministic template. Walks a
  `CasualtyNode` and composes a structured summary: priority
  band, top trauma hypothesis, the two highest-weight reasons,
  confidence range.
- **LLM grounding** — optional, see section 3.

The template builder is the default for every UI / dashboard
surface. It is tested via `tests/test_explainability.py`.

## 2. Example

```python
from triage4.core.models import CasualtySignature
from triage4.triage_reasoning import (
    RapidTriageEngine,
    UncertaintyModel,
    ExplainabilityBuilder,
)

sig = CasualtySignature(
    bleeding_visual_score=0.91,
    perfusion_drop_score=0.82,
    chest_motion_fd=0.08,
    breathing_curve=[0.01, 0.02] * 3,
    raw_features={"bleeding_confidence": 0.90, "breathing_quality": 0.85},
)

engine = RapidTriageEngine()
priority, score, reasons = engine.infer_priority(sig)
# priority = "immediate"
# reasons = ["mortal-sign override (bleeding_visual_score >= 0.80)", ...]

uncertainty = UncertaintyModel().from_signature(sig, base_score=score)
# uncertainty.per_channel_confidence = {"bleeding": 0.90, "breathing": 0.85, ...}
# uncertainty.adjusted_score = 0.94 * 0.88 ≈ 0.83
```

The `examples/quick_triage.py` script runs exactly this path end-
to-end.

## 3. LLM grounding (optional, off by default)

`triage_reasoning/llm_grounding.py` ships a **grounded prompt
builder**: it takes the priority + score + reasons + confidence
and composes a prompt that forces the LLM to only **phrase** what
triage4 already decided.

Key design points:

- **Default backend is `TemplateGroundingBackend`** — no LLM call,
  fully deterministic, runs everywhere.
- **LLM path is a `Protocol`** — any provider (OpenAI, Anthropic,
  local LLaMA) that implements `LLMBackend.complete(prompt) -> str`
  can be attached without code changes to triage4.
- **Grounded prompt format** — includes every numeric fact the
  engine already produced. The LLM is asked to **not introduce
  facts** and to **keep the priority band unchanged**. The prompt
  template lives in
  `triage_reasoning/llm_grounding.py::build_prompt`.
- **Backend returns a string only**; triage4 never reads a
  priority, score, or threshold from the LLM output. Hallucinated
  clinical content cannot leak into the decision path.

This matches `REGULATORY.md §7`: the classifier is locked; the
LLM is a phrasing tool, not a clinician.

## 4. Observability

Once deployed:

- **Dashboard** — `GET /casualties/{id}/explain` returns the
  structured explanation. The UI renders priority + reasons +
  confidence bars.
- **Logs** — when `telemetry.structured_json: true` (default in
  `configs/production.yaml`), every triage decision is logged with
  the reasons list attached. Useful for post-mission audit.
- **Prometheus** — `/metrics` exposes
  `triage4_casualties_total{priority="..."}` and handoff latency
  histogram so an upstream dashboard can surface *patterns* even
  without reading individual records.

## 5. Non-goals

- **No free-form clinical reasoning.** Reasons are enumerations,
  not open narratives.
- **No feature attribution via SHAP / LIME.** The fusion is so
  small (4 channels, one linear combination) that direct
  inspection of the contributions beats any post-hoc attribution.
- **No saliency maps.** If you need pixel-level attribution on a
  vision model, attach that at the detector layer
  (`perception/yolo_detector.py`) — it is out of scope here.

## 6. References

- `triage_reasoning/rapid_triage.py` — reason generation.
- `triage_reasoning/score_fusion.py` — mortal-sign override.
- `triage_reasoning/uncertainty.py` — per-channel confidence.
- `triage_reasoning/explainability.py` — template summary.
- `triage_reasoning/llm_grounding.py` — grounded prompt + Protocol.
- `examples/quick_triage.py` — runnable end-to-end.
- `docs/SAFETY_CASE.md §G3` — operator-in-the-loop safety argument.
