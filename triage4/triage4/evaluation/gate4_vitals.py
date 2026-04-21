"""Gate 4 — Accurate vitals (optional).

Evaluates predicted heart-rate and respiration-rate accuracy against
ground-truth.

Metrics:
- MAE and RMSE for HR and RR separately;
- tolerance-hit rate — the fraction of predictions that fall within a
  per-vital absolute tolerance (DARPA-style accuracy gates);
- mean absolute percentage error.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple

import numpy as np


@dataclass
class VitalMetrics:
    n: int
    mae: float
    rmse: float
    tolerance_hit_rate: float
    mape: float


@dataclass
class Gate4Report:
    hr: VitalMetrics
    rr: VitalMetrics
    params: dict


def _metrics(
    preds: list[float], truths: list[float], tolerance: float
) -> VitalMetrics:
    if not preds:
        return VitalMetrics(
            n=0, mae=0.0, rmse=0.0, tolerance_hit_rate=0.0, mape=0.0
        )
    p = np.asarray(preds, dtype=np.float64)
    t = np.asarray(truths, dtype=np.float64)
    diff = p - t
    mae = float(np.mean(np.abs(diff)))
    rmse = float(np.sqrt(np.mean(diff ** 2)))
    hits = float(np.mean(np.abs(diff) <= tolerance))
    with np.errstate(divide="ignore", invalid="ignore"):
        mask = t != 0.0
        if mask.any():
            mape = float(np.mean(np.abs(diff[mask] / t[mask])))
        else:
            mape = 0.0
    return VitalMetrics(
        n=len(preds),
        mae=round(mae, 3),
        rmse=round(rmse, 3),
        tolerance_hit_rate=round(hits, 3),
        mape=round(mape, 3),
    )


def evaluate_gate4(
    predictions: Mapping[str, Tuple[float, float]],
    truths: Mapping[str, Tuple[float, float]],
    hr_tolerance_bpm: float = 10.0,
    rr_tolerance_bpm: float = 3.0,
) -> Gate4Report:
    """Evaluate HR and RR accuracy.

    ``predictions`` / ``truths`` map ``casualty_id -> (hr_bpm, rr_bpm)``.
    Only ids present in both are scored.
    """
    if hr_tolerance_bpm <= 0 or rr_tolerance_bpm <= 0:
        raise ValueError("tolerances must be > 0")

    common_ids = sorted(set(predictions) & set(truths))
    hr_preds, hr_truths, rr_preds, rr_truths = [], [], [], []
    for cid in common_ids:
        hr_p, rr_p = predictions[cid]
        hr_t, rr_t = truths[cid]
        hr_preds.append(float(hr_p))
        hr_truths.append(float(hr_t))
        rr_preds.append(float(rr_p))
        rr_truths.append(float(rr_t))

    return Gate4Report(
        hr=_metrics(hr_preds, hr_truths, hr_tolerance_bpm),
        rr=_metrics(rr_preds, rr_truths, rr_tolerance_bpm),
        params={
            "hr_tolerance_bpm": hr_tolerance_bpm,
            "rr_tolerance_bpm": rr_tolerance_bpm,
        },
    )
