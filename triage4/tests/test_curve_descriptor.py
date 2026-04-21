import numpy as np
import pytest

from triage4.matching import (
    CurveDescriptor,
    CurveDescriptorConfig,
    batch_describe_curves,
    compute_curvature_profile,
    compute_fourier_descriptor,
    describe_curve,
    descriptor_distance,
    descriptor_similarity,
    find_best_match,
)


def _circle(n: int = 128, r: float = 1.0) -> np.ndarray:
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([r * np.cos(t), r * np.sin(t)])


def _line(n: int = 64) -> np.ndarray:
    return np.column_stack([np.linspace(0, 1, n), np.zeros(n)])


def test_fourier_descriptor_shape():
    fd = compute_fourier_descriptor(_circle(128), n_harmonics=8)
    assert fd.shape == (8,)


def test_fourier_descriptor_pads_short_curve():
    fd = compute_fourier_descriptor(
        np.array([[0.0, 0.0], [1.0, 0.0]]), n_harmonics=8
    )
    assert fd.shape == (8,)


def test_fourier_descriptor_rejects_bad_shape():
    with pytest.raises(ValueError):
        compute_fourier_descriptor(np.array([0.0, 1.0, 2.0]))


def test_curvature_profile_straight_line_is_zero():
    cp = compute_curvature_profile(_line(32))
    assert np.allclose(cp, 0.0)


def test_curvature_profile_circle_is_constant_sign():
    cp = compute_curvature_profile(_circle(64))
    interior = cp[1:-1]
    assert np.all(interior > 0) or np.all(interior < 0)


def test_describe_curve_returns_descriptor_with_expected_fields():
    cfg = CurveDescriptorConfig(n_harmonics=5, resample_n=32)
    d = describe_curve(_circle(128), cfg)
    assert isinstance(d, CurveDescriptor)
    assert d.fourier_desc.shape == (5,)
    assert d.arc_length > 0.0
    assert d.n_points == 128


def test_descriptor_distance_identical_is_zero():
    d = describe_curve(_circle(128))
    assert descriptor_distance(d, d) == pytest.approx(0.0)


def test_descriptor_similarity_identical_is_one():
    d = describe_curve(_circle(128))
    assert descriptor_similarity(d, d, sigma=1.0) == pytest.approx(1.0)


def test_descriptor_similarity_rejects_bad_sigma():
    d = describe_curve(_circle(128))
    with pytest.raises(ValueError):
        descriptor_similarity(d, d, sigma=0.0)


def test_find_best_match_returns_closest():
    q = describe_curve(_circle(128, r=1.0))
    candidates = [
        describe_curve(_line(64)),
        describe_curve(_circle(128, r=1.001)),  # nearly identical to q
        describe_curve(_circle(64, r=5.0)),
    ]
    idx, dist = find_best_match(q, candidates)
    assert idx == 1
    assert dist >= 0.0


def test_find_best_match_empty_raises():
    q = describe_curve(_circle(128))
    with pytest.raises(ValueError):
        find_best_match(q, [])


def test_batch_describe_returns_list():
    descs = batch_describe_curves([_circle(64), _line(64)])
    assert len(descs) == 2
    for d in descs:
        assert isinstance(d, CurveDescriptor)


def test_resample_accepts_short_curve():
    cfg = CurveDescriptorConfig(resample_n=8)
    d = describe_curve(np.array([[0.0, 0.0], [1.0, 0.0]]), cfg)
    assert d.n_points == 2
