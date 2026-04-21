"""Gate 3 — Trauma assessment.

Evaluates whether the system detected the right *set* of trauma
hypotheses per casualty. Each casualty can carry zero-to-many trauma
labels (``hemorrhage``, ``respiratory_distress``, ``shock_risk``, …), so
this is a multi-label problem.

Returns per-kind precision / recall / F1 plus the macro and micro
aggregates, as well as per-casualty Hamming accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping


@dataclass
class LabelMetrics:
    label: str
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


@dataclass
class Gate3Report:
    macro_f1: float
    micro_f1: float
    mean_hamming_accuracy: float
    per_label: Dict[str, LabelMetrics] = field(default_factory=dict)


def _as_set(values: Iterable[str]) -> set[str]:
    return {str(v) for v in values}


def evaluate_gate3(
    predictions: Mapping[str, Iterable[str]],
    truths: Mapping[str, Iterable[str]],
) -> Gate3Report:
    """Evaluate multi-label trauma hypotheses.

    ``predictions`` / ``truths`` map ``casualty_id -> set of trauma kinds``.
    Only casualty ids present in both are scored.
    """
    common_ids = sorted(set(predictions) & set(truths))

    all_labels: set[str] = set()
    for cid in common_ids:
        all_labels.update(_as_set(predictions[cid]))
        all_labels.update(_as_set(truths[cid]))

    per_label: Dict[str, LabelMetrics] = {
        label: LabelMetrics(label=label, tp=0, fp=0, fn=0) for label in all_labels
    }

    hamming_scores: list[float] = []

    for cid in common_ids:
        pred_set = _as_set(predictions[cid])
        truth_set = _as_set(truths[cid])
        union = pred_set | truth_set

        for label in union:
            m = per_label.setdefault(
                label, LabelMetrics(label=label, tp=0, fp=0, fn=0)
            )
            if label in pred_set and label in truth_set:
                m.tp += 1
            elif label in pred_set:
                m.fp += 1
            elif label in truth_set:
                m.fn += 1

        if union:
            intersect = len(pred_set & truth_set)
            hamming_scores.append(intersect / len(union))
        else:
            hamming_scores.append(1.0)

    if not common_ids:
        return Gate3Report(
            macro_f1=0.0, micro_f1=0.0, mean_hamming_accuracy=0.0
        )

    if not per_label:
        # No trauma labels at all on either side — perfect trivial agreement.
        mean_hamming = (
            sum(hamming_scores) / len(hamming_scores) if hamming_scores else 0.0
        )
        return Gate3Report(
            macro_f1=1.0,
            micro_f1=1.0,
            mean_hamming_accuracy=round(mean_hamming, 3),
        )

    tp_total = sum(m.tp for m in per_label.values())
    fp_total = sum(m.fp for m in per_label.values())
    fn_total = sum(m.fn for m in per_label.values())

    micro_p = tp_total / (tp_total + fp_total) if (tp_total + fp_total) > 0 else 0.0
    micro_r = tp_total / (tp_total + fn_total) if (tp_total + fn_total) > 0 else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) > 0 else 0.0

    macro_f1 = sum(m.f1 for m in per_label.values()) / len(per_label)

    mean_hamming = sum(hamming_scores) / len(hamming_scores) if hamming_scores else 0.0

    return Gate3Report(
        macro_f1=round(macro_f1, 3),
        micro_f1=round(micro_f1, 3),
        mean_hamming_accuracy=round(mean_hamming, 3),
        per_label=per_label,
    )
