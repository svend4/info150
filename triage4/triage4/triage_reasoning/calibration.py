"""Weight and threshold calibration from labelled data.

Part of Phase 9b. Given a labelled synthetic dataset (see
:mod:`triage4.sim.realistic_dataset`), re-tunes:

- per-band score thresholds (immediate / delayed / minimal);
- fusion weights over the four score-fusion channels.

Uses grid search with :func:`select_f1_threshold` and ``Gate2Report``
metrics already available in ``scoring/`` and ``evaluation/``. Small,
honest, transparent — not an ML trainer.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable

from triage4.evaluation import evaluate_gate2
from triage4.sim.realistic_dataset import LabelledCase
from triage4.triage_reasoning.rapid_triage import RapidTriageEngine
from triage4.triage_reasoning.score_fusion import (
    DEFAULT_WEIGHTS,
    fuse_triage_score,
    priority_from_score,
)


@dataclass
class CalibrationResult:
    weights: dict[str, float]
    immediate_threshold: float
    delayed_threshold: float
    accuracy: float
    macro_f1: float
    critical_miss_rate: float
    n_cases: int


def _evaluate_config(
    cases: Iterable[LabelledCase],
    weights: dict[str, float],
    immediate_threshold: float,
    delayed_threshold: float,
) -> CalibrationResult:
    preds: list[tuple[str, str]] = []
    truths: list[tuple[str, str]] = []
    total = 0
    for case in cases:
        combined = fuse_triage_score(case.signature, weights)
        # Apply custom thresholds then the mortal-sign override inside
        # priority_from_score (sig=... drives that logic).
        band = _band_for_score(
            combined.score,
            immediate_threshold=immediate_threshold,
            delayed_threshold=delayed_threshold,
        )
        if band == "immediate":
            priority = priority_from_score(1.0, sig=case.signature)
        else:
            # Still let mortal-sign override catch isolated-mortal cases.
            mortal_priority = priority_from_score(0.0, sig=case.signature)
            priority = "immediate" if mortal_priority == "immediate" else band

        preds.append((case.casualty_id, priority))
        truths.append((case.casualty_id, case.priority))
        total += 1

    report = evaluate_gate2(preds, truths)
    return CalibrationResult(
        weights=dict(weights),
        immediate_threshold=immediate_threshold,
        delayed_threshold=delayed_threshold,
        accuracy=report.accuracy,
        macro_f1=report.macro_f1,
        critical_miss_rate=report.critical_miss_rate,
        n_cases=total,
    )


def _band_for_score(
    score: float, immediate_threshold: float, delayed_threshold: float
) -> str:
    if score >= immediate_threshold:
        return "immediate"
    if score >= delayed_threshold:
        return "delayed"
    return "minimal"


def calibrate(
    cases: list[LabelledCase],
    weight_grid: list[dict[str, float]] | None = None,
    immediate_thresholds: list[float] | None = None,
    delayed_thresholds: list[float] | None = None,
) -> CalibrationResult:
    """Grid-search for the best configuration.

    Criterion: minimise ``critical_miss_rate`` first, then maximise
    ``macro_f1`` (tie-break). That ordering matches the clinical
    priority — never miss an ``immediate``, then try to be right on
    the rest.
    """
    if not cases:
        raise ValueError("cases must not be empty")

    weight_grid = weight_grid or _default_weight_grid()
    immediate_thresholds = immediate_thresholds or [0.55, 0.60, 0.65, 0.70]
    delayed_thresholds = delayed_thresholds or [0.25, 0.30, 0.35, 0.40]

    best: CalibrationResult | None = None
    for weights, imm_th, del_th in product(
        weight_grid, immediate_thresholds, delayed_thresholds
    ):
        if imm_th <= del_th:
            continue
        result = _evaluate_config(cases, weights, imm_th, del_th)
        if best is None or (
            (result.critical_miss_rate, -result.macro_f1)
            < (best.critical_miss_rate, -best.macro_f1)
        ):
            best = result
    assert best is not None
    return best


def _default_weight_grid() -> list[dict[str, float]]:
    """Small search grid. Stays inside ± ~30% of the current defaults."""
    grid: list[dict[str, float]] = []
    for bleeding, motion, perfusion in product(
        (0.35, 0.45, 0.55), (0.20, 0.30, 0.40), (0.15, 0.20, 0.25)
    ):
        posture = max(0.01, 1.0 - bleeding - motion - perfusion)
        grid.append(
            {
                "bleeding": bleeding,
                "chest_motion": motion,
                "perfusion": perfusion,
                "posture": posture,
            }
        )
    # Include the current DEFAULT_WEIGHTS explicitly.
    grid.append(dict(DEFAULT_WEIGHTS))
    return grid


def build_engine_from_result(
    result: CalibrationResult,
) -> RapidTriageEngine:
    """Hand a calibration result back to a ready-to-run engine."""
    return RapidTriageEngine(weights=result.weights)


def evaluate_engine_on_dataset(
    engine: RapidTriageEngine, cases: list[LabelledCase]
) -> CalibrationResult:
    """Score an already-configured engine on a labelled dataset."""
    preds = []
    truths = []
    for case in cases:
        priority, _, _ = engine.infer_priority(case.signature)
        preds.append((case.casualty_id, priority))
        truths.append((case.casualty_id, case.priority))
    r = evaluate_gate2(preds, truths)
    return CalibrationResult(
        weights=dict(engine.weights),
        immediate_threshold=0.65,
        delayed_threshold=0.35,
        accuracy=r.accuracy,
        macro_f1=r.macro_f1,
        critical_miss_rate=r.critical_miss_rate,
        n_cases=len(cases),
    )
