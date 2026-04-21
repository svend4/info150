"""Gate 1 — Find and locate.

DARPA Triage Challenge Event 3 Gate 1 asks whether the autonomous
system can find casualties in the arena and localise them accurately.

This evaluator takes predicted (x, y) positions and ground-truth
(x, y) positions and produces:

- precision / recall / F1 under a match-distance tolerance;
- mean / max localisation error for matched pairs;
- lists of TP / FP / FN ids for audit.

Matching is done greedily nearest-first, each ground-truth casualty
can be matched to at most one prediction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

import numpy as np


@dataclass
class Gate1Report:
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float
    mean_localization_error: float
    max_localization_error: float
    matched_pairs: List[Tuple[str, str]] = field(default_factory=list)
    unmatched_preds: List[str] = field(default_factory=list)
    unmatched_truths: List[str] = field(default_factory=list)
    params: Dict[str, float] = field(default_factory=dict)


def _f1(p: float, r: float) -> float:
    return (2 * p * r / (p + r)) if (p + r) > 0 else 0.0


def evaluate_gate1(
    predictions: Sequence[Tuple[str, float, float]],
    truths: Sequence[Tuple[str, float, float]],
    match_distance: float = 5.0,
) -> Gate1Report:
    """Evaluate find-and-locate.

    ``predictions`` and ``truths`` are each a list of ``(id, x, y)``. A
    predicted casualty counts as a TP if there exists an unmatched truth
    within ``match_distance`` of it. Greedy nearest-first.
    """
    if match_distance <= 0:
        raise ValueError(f"match_distance must be > 0, got {match_distance}")

    pred_list = list(predictions)
    truth_list = list(truths)

    if not pred_list and not truth_list:
        return Gate1Report(
            tp=0, fp=0, fn=0,
            precision=0.0, recall=0.0, f1=0.0,
            mean_localization_error=0.0,
            max_localization_error=0.0,
            params={"match_distance": match_distance},
        )

    # Build distance matrix.
    pred_xy = np.array([[p[1], p[2]] for p in pred_list], dtype=np.float64)
    truth_xy = np.array([[t[1], t[2]] for t in truth_list], dtype=np.float64)

    if len(pred_xy) == 0:
        return Gate1Report(
            tp=0, fp=0, fn=len(truth_list),
            precision=0.0, recall=0.0, f1=0.0,
            mean_localization_error=0.0,
            max_localization_error=0.0,
            unmatched_truths=[t[0] for t in truth_list],
            params={"match_distance": match_distance},
        )
    if len(truth_xy) == 0:
        return Gate1Report(
            tp=0, fp=len(pred_list), fn=0,
            precision=0.0, recall=0.0, f1=0.0,
            mean_localization_error=0.0,
            max_localization_error=0.0,
            unmatched_preds=[p[0] for p in pred_list],
            params={"match_distance": match_distance},
        )

    dist = np.linalg.norm(
        pred_xy[:, None, :] - truth_xy[None, :, :], axis=-1
    )

    # Greedy nearest-first assignment.
    used_preds: set[int] = set()
    used_truths: set[int] = set()
    matched: List[Tuple[str, str]] = []
    errors: List[float] = []

    while True:
        # Mask already-used rows/cols.
        working = dist.copy()
        for i in used_preds:
            working[i, :] = np.inf
        for j in used_truths:
            working[:, j] = np.inf
        if not np.isfinite(working).any():
            break

        i, j = divmod(int(np.argmin(working)), working.shape[1])
        d = float(working[i, j])
        if d > match_distance:
            break
        used_preds.add(i)
        used_truths.add(j)
        matched.append((pred_list[i][0], truth_list[j][0]))
        errors.append(d)

    tp = len(matched)
    fp = len(pred_list) - tp
    fn = len(truth_list) - tp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    return Gate1Report(
        tp=tp, fp=fp, fn=fn,
        precision=round(precision, 3),
        recall=round(recall, 3),
        f1=round(_f1(precision, recall), 3),
        mean_localization_error=round(float(np.mean(errors)), 3) if errors else 0.0,
        max_localization_error=round(float(np.max(errors)), 3) if errors else 0.0,
        matched_pairs=matched,
        unmatched_preds=[
            pred_list[i][0] for i in range(len(pred_list)) if i not in used_preds
        ],
        unmatched_truths=[
            truth_list[j][0] for j in range(len(truth_list)) if j not in used_truths
        ],
        params={"match_distance": match_distance},
    )
