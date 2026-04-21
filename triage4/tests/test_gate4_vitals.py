import pytest

from triage4.evaluation import Gate4Report, VitalMetrics, evaluate_gate4


def test_gate4_perfect_match():
    preds = {"C1": (72.0, 15.0), "C2": (80.0, 18.0)}
    truths = {"C1": (72.0, 15.0), "C2": (80.0, 18.0)}
    r = evaluate_gate4(preds, truths)
    assert isinstance(r, Gate4Report)
    assert r.hr.mae == 0.0
    assert r.hr.tolerance_hit_rate == 1.0
    assert r.rr.mae == 0.0


def test_gate4_mae_and_rmse():
    preds = {"C1": (80.0, 20.0)}
    truths = {"C1": (70.0, 15.0)}
    r = evaluate_gate4(preds, truths)
    assert r.hr.mae == pytest.approx(10.0)
    assert r.rr.mae == pytest.approx(5.0)


def test_gate4_tolerance_hits():
    preds = {"C1": (75.0, 15.0), "C2": (100.0, 40.0)}  # C2 way off
    truths = {"C1": (72.0, 15.0), "C2": (80.0, 18.0)}
    r = evaluate_gate4(preds, truths, hr_tolerance_bpm=10.0, rr_tolerance_bpm=3.0)
    # C1 is within tolerance for both, C2 is outside.
    assert r.hr.tolerance_hit_rate == 0.5
    assert r.rr.tolerance_hit_rate == 0.5


def test_gate4_empty_inputs():
    r = evaluate_gate4({}, {})
    assert r.hr.n == 0
    assert r.rr.n == 0
    assert r.hr.mae == 0.0


def test_gate4_rejects_non_positive_tolerance():
    with pytest.raises(ValueError):
        evaluate_gate4({}, {}, hr_tolerance_bpm=0.0)
    with pytest.raises(ValueError):
        evaluate_gate4({}, {}, rr_tolerance_bpm=-1.0)


def test_gate4_missing_ids_ignored():
    preds = {"C1": (72.0, 15.0), "C_unknown": (60.0, 10.0)}
    truths = {"C1": (72.0, 15.0)}
    r = evaluate_gate4(preds, truths)
    assert r.hr.n == 1


def test_gate4_vital_metrics_is_dataclass():
    m = VitalMetrics(n=1, mae=0.0, rmse=0.0, tolerance_hit_rate=1.0, mape=0.0)
    assert m.n == 1
