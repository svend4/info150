"""Phase 9b unit tests — YOLO, realistic dataset, calibrator, physionet."""

from __future__ import annotations

import numpy as np
import pytest

from triage4.integrations import (
    PhysioNetRecord,
    PhysioNetUnavailable,
    load_dict,
    load_wfdb,
)
from triage4.perception import (
    DetectorUnavailable,
    LoopbackYOLODetector,
    build_ultralytics_detector,
)
from triage4.sim.realistic_dataset import LabelledCase, generate_labelled_dataset
from triage4.triage_reasoning.calibration import (
    CalibrationResult,
    calibrate,
    evaluate_engine_on_dataset,
)
from triage4.triage_reasoning.rapid_triage import RapidTriageEngine


# ---- YOLO detector ---------------------------------------------------------


def test_loopback_yolo_returns_canned_detections_in_order():
    detector = LoopbackYOLODetector(
        canned_detections=[
            [{"bbox": [0, 0, 10, 20], "score": 0.9}],
            [{"bbox": [30, 30, 40, 40], "score": 0.7}],
            [],
        ]
    )
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    r1 = detector.detect(frame)
    r2 = detector.detect(frame)
    r3 = detector.detect(frame)
    assert len(r1) == 1 and r1[0]["score"] == 0.9
    assert len(r2) == 1 and r2[0]["bbox"] == [30, 30, 40, 40]
    assert r3 == []
    assert detector.call_count == 3


def test_loopback_yolo_applies_confidence_floor():
    detector = LoopbackYOLODetector(
        canned_detections=[
            [{"bbox": [0, 0, 10, 20], "score": 0.3},
             {"bbox": [30, 30, 40, 40], "score": 0.9}]
        ],
        confidence_floor=0.5,
    )
    out = detector.detect(np.zeros((10, 10, 3)))
    assert len(out) == 1
    assert out[0]["score"] == 0.9


def test_loopback_yolo_empty_after_exhaustion():
    detector = LoopbackYOLODetector(canned_detections=[[{"bbox": [0, 0, 1, 1], "score": 1.0}]])
    detector.detect(np.zeros((1, 1, 3)))
    assert detector.detect(np.zeros((1, 1, 3))) == []


def test_loopback_yolo_reload_resets_counter():
    detector = LoopbackYOLODetector()
    detector.load([[{"bbox": [0, 0, 1, 1], "score": 0.9}]])
    assert detector.call_count == 0
    out = detector.detect(np.zeros((1, 1, 3)))
    assert len(out) == 1


def test_loopback_yolo_confidence_floor_validation():
    with pytest.raises(ValueError):
        LoopbackYOLODetector(confidence_floor=1.5)


def test_build_ultralytics_detector_raises_when_missing():
    try:
        import ultralytics  # noqa: F401
    except ImportError:
        with pytest.raises(DetectorUnavailable):
            build_ultralytics_detector()
    else:
        pytest.skip("ultralytics installed")


# ---- Realistic dataset -----------------------------------------------------


def test_realistic_dataset_shape_and_coverage():
    cases = generate_labelled_dataset(n_per_scenario=3, seed=0)
    assert len(cases) == 21  # 7 scenarios × 3
    tags = {c.scenario_tag for c in cases}
    assert {
        "clean_immediate",
        "clean_delayed",
        "clean_minimal",
        "isolated_bleeding",
        "isolated_no_breathing",
        "isolated_collapsed",
        "ambiguous_mid",
    } == tags


def test_realistic_dataset_cases_have_ground_truth():
    cases = generate_labelled_dataset(n_per_scenario=2, seed=1)
    priorities = {c.priority for c in cases}
    assert priorities <= {"immediate", "delayed", "minimal"}
    for c in cases:
        assert isinstance(c, LabelledCase)
        assert c.signature is not None


def test_realistic_dataset_is_deterministic_by_seed():
    a = generate_labelled_dataset(n_per_scenario=2, seed=123)
    b = generate_labelled_dataset(n_per_scenario=2, seed=123)
    assert [c.casualty_id for c in a] == [c.casualty_id for c in b]
    for ca, cb in zip(a, b):
        assert ca.signature.bleeding_visual_score == cb.signature.bleeding_visual_score


# ---- Calibration -----------------------------------------------------------


def test_calibrate_returns_best_configuration():
    cases = generate_labelled_dataset(n_per_scenario=5, seed=7)
    result = calibrate(cases)
    assert isinstance(result, CalibrationResult)
    assert result.n_cases == len(cases)
    assert 0.0 <= result.critical_miss_rate <= 1.0
    assert 0.0 <= result.accuracy <= 1.0
    assert result.immediate_threshold > result.delayed_threshold


def test_calibrate_empty_raises():
    with pytest.raises(ValueError):
        calibrate([])


def test_calibrated_engine_keeps_critical_miss_low():
    """Mortal-sign override must keep critical_miss_rate low on noisy data.

    On clean data the override guarantees zero misses (next test); on
    sensor-degraded data the noise can push a bleeding value of 0.82
    down to 0.79 for one frame, slipping it under the threshold. We
    require ≤ 15% miss rate — calibration keeps this low, not zero.
    """
    cases = generate_labelled_dataset(n_per_scenario=4, seed=11)
    result = calibrate(cases)
    assert result.critical_miss_rate <= 0.15


def test_rapid_triage_mortal_override_on_clean_signals_is_perfect():
    """No noise, no degradation — the override must be flawless."""
    cases = generate_labelled_dataset(
        n_per_scenario=5, seed=33, apply_degradation=False
    )
    result = evaluate_engine_on_dataset(RapidTriageEngine(), cases)
    assert result.critical_miss_rate == 0.0


def test_evaluate_engine_on_dataset():
    cases = generate_labelled_dataset(n_per_scenario=3, seed=0)
    engine = RapidTriageEngine()
    result = evaluate_engine_on_dataset(engine, cases)
    assert result.n_cases == len(cases)
    assert 0.0 <= result.accuracy <= 1.0


# ---- PhysioNet adapter -----------------------------------------------------


def test_physionet_load_dict_basic():
    rec = load_dict(
        "rec_01",
        fs_hz=100.0,
        pulse=np.sin(np.linspace(0, 10, 1000)),
        respiration=np.sin(np.linspace(0, 2, 1000)),
    )
    assert isinstance(rec, PhysioNetRecord)
    assert rec.record_id == "rec_01"
    assert rec.pulse.shape == (1000,)
    assert rec.respiration.shape == (1000,)


def test_physionet_record_validates_inputs():
    with pytest.raises(ValueError):
        PhysioNetRecord(
            record_id="x",
            fs_hz=0.0,
            pulse=np.zeros(10),
            respiration=np.zeros(10),
        )
    with pytest.raises(ValueError):
        PhysioNetRecord(
            record_id="x",
            fs_hz=100.0,
            pulse=np.zeros((2, 2)),
            respiration=np.zeros(10),
        )


def test_physionet_load_wfdb_raises_when_missing():
    try:
        import wfdb  # noqa: F401
    except ImportError:
        with pytest.raises(PhysioNetUnavailable):
            load_wfdb("bogus/path")
    else:
        pytest.skip("wfdb installed")


def test_physionet_record_integrates_with_vitals_estimator():
    from triage4.triage_reasoning import VitalsEstimator

    # 1.2 Hz pulse (72 bpm), 0.3 Hz breathing (18 bpm).
    fs = 30.0
    t = np.arange(600) / fs
    rec = load_dict(
        "rec_vitals",
        fs_hz=fs,
        pulse=np.sin(2 * np.pi * 1.2 * t),
        respiration=np.sin(2 * np.pi * 0.3 * t),
    )
    vitals = VitalsEstimator().estimate(
        breathing_curve=list(rec.respiration),
        perfusion_series=list(rec.pulse),
        fs_hz=rec.fs_hz,
    )
    assert 60.0 <= vitals.heart_rate_bpm <= 90.0
    assert 12.0 <= vitals.respiration_rate_bpm <= 25.0
