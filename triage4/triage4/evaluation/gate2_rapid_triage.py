"""Gate 2 — Rapid triage.

Evaluates whether the system assigns the correct triage priority
(``immediate`` / ``delayed`` / ``minimal`` / ``expectant`` / ``unknown``)
to each casualty.

Core metric is overall accuracy plus per-class precision / recall / F1.
An extra ``critical_miss_rate`` separately counts the fraction of
ground-truth ``immediate`` casualties that were labelled as anything
else — those are the errors that can get someone killed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Sequence, Tuple

import numpy as np


_DEFAULT_CLASSES = ("immediate", "delayed", "minimal", "expectant", "unknown")


@dataclass
class ClassMetrics:
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
class Gate2Report:
    accuracy: float
    macro_f1: float
    critical_miss_rate: float
    confusion: np.ndarray
    per_class: Dict[str, ClassMetrics] = field(default_factory=dict)
    class_labels: Tuple[str, ...] = _DEFAULT_CLASSES


def evaluate_gate2(
    predictions: Sequence[Tuple[str, str]],
    truths: Sequence[Tuple[str, str]],
    class_labels: Tuple[str, ...] = _DEFAULT_CLASSES,
    critical_class: str = "immediate",
) -> Gate2Report:
    """Evaluate rapid-triage priority classification.

    ``predictions`` and ``truths`` are each a list of ``(casualty_id, label)``.
    Pairs are matched by casualty id; any id present in one but not the
    other is silently ignored.
    """
    if not class_labels:
        raise ValueError("class_labels must not be empty")
    if critical_class not in class_labels:
        raise ValueError(
            f"critical_class {critical_class!r} not in class_labels"
        )

    pred_by_id = {cid: label for cid, label in predictions}
    truth_by_id = {cid: label for cid, label in truths}
    common_ids = sorted(set(pred_by_id) & set(truth_by_id))

    label_idx = {label: i for i, label in enumerate(class_labels)}
    n_classes = len(class_labels)
    confusion = np.zeros((n_classes, n_classes), dtype=np.int64)

    n_total = 0
    n_correct = 0
    critical_truth = 0
    critical_missed = 0

    for cid in common_ids:
        y_true = truth_by_id[cid]
        y_pred = pred_by_id[cid]
        if y_true not in label_idx or y_pred not in label_idx:
            continue
        n_total += 1
        if y_true == y_pred:
            n_correct += 1
        confusion[label_idx[y_true], label_idx[y_pred]] += 1

        if y_true == critical_class:
            critical_truth += 1
            if y_pred != critical_class:
                critical_missed += 1

    per_class: Dict[str, ClassMetrics] = {}
    for label, i in label_idx.items():
        tp = int(confusion[i, i])
        fp = int(confusion[:, i].sum() - tp)
        fn = int(confusion[i, :].sum() - tp)
        per_class[label] = ClassMetrics(label=label, tp=tp, fp=fp, fn=fn)

    accuracy = n_correct / n_total if n_total > 0 else 0.0
    macro_f1 = (
        float(np.mean([m.f1 for m in per_class.values()]))
        if per_class
        else 0.0
    )
    critical_miss_rate = (
        critical_missed / critical_truth if critical_truth > 0 else 0.0
    )

    return Gate2Report(
        accuracy=round(accuracy, 3),
        macro_f1=round(macro_f1, 3),
        critical_miss_rate=round(critical_miss_rate, 3),
        confusion=confusion,
        per_class=per_class,
        class_labels=class_labels,
    )
