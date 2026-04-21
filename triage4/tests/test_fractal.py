import math

import numpy as np

from triage4.signatures.fractal import (
    BoxCountingFD,
    RichardsonDivider,
    box_counting_fd,
    css_similarity,
    css_similarity_mirror,
    css_to_feature_vector,
    curvature_scale_space,
    divider_fd,
    freeman_chain_code,
    mask_to_contour,
)
from triage4.signatures.fractal_motion import FractalMotionAnalyzer


def _circle_contour(n: int = 128, radius: float = 10.0) -> np.ndarray:
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack([radius * np.cos(theta), radius * np.sin(theta)])


def _square_contour(n_per_side: int = 32, side: float = 10.0) -> np.ndarray:
    t = np.linspace(0, side, n_per_side, endpoint=False)
    top = np.column_stack([t, np.full_like(t, side)])
    right = np.column_stack([np.full_like(t, side), side - t])
    bottom = np.column_stack([side - t, np.zeros_like(t)])
    left = np.column_stack([np.zeros_like(t), t])
    return np.vstack([top, right, bottom, left])


def test_box_counting_on_straight_line_is_near_1():
    contour = np.column_stack([np.arange(64, dtype=float), np.zeros(64)])
    fd = box_counting_fd(contour, n_scales=5)
    assert 1.0 <= fd <= 1.2


def test_box_counting_on_circle_is_between_1_and_2():
    fd = box_counting_fd(_circle_contour(256, radius=20), n_scales=6)
    assert 1.0 <= fd <= 2.0


def test_box_counting_fd_object_accepts_mask():
    mask = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
    fd = BoxCountingFD(n_scales=3).estimate(mask)
    assert 0.0 <= fd <= 2.0


def test_divider_on_straight_line_near_1():
    contour = np.column_stack([np.arange(128, dtype=float), np.zeros(128)])
    fd = divider_fd(contour, n_scales=6)
    assert 1.0 <= fd <= 1.1


def test_divider_on_circle_near_1():
    fd = divider_fd(_circle_contour(512, radius=50), n_scales=6)
    assert 1.0 <= fd <= 1.3


def test_richardson_divider_object_on_signal():
    signal = [math.sin(i / 3.0) for i in range(128)]
    fd = RichardsonDivider(n_scales=6).estimate_1d(signal)
    assert 1.0 <= fd <= 2.0


def test_richardson_divider_short_signal_is_zero():
    assert RichardsonDivider().estimate_1d([0.0, 1.0]) == 0.0


def test_mask_to_contour_roundtrip():
    mask = [[1, 0], [0, 1]]
    pts = mask_to_contour(mask)
    assert sorted(map(tuple, pts.tolist())) == [(0.0, 0.0), (1.0, 1.0)]


def test_css_circle_vs_square_similarity_less_than_self():
    circle = _circle_contour(128, radius=10.0)
    square = _square_contour(32, side=10.0)

    vec_c = css_to_feature_vector(curvature_scale_space(circle, n_sigmas=5), n_bins=32)
    vec_s = css_to_feature_vector(curvature_scale_space(square, n_sigmas=5), n_bins=32)

    self_sim = css_similarity(vec_c, vec_c)
    cross_sim = css_similarity(vec_c, vec_s)

    assert 0.98 <= self_sim <= 1.0001
    assert cross_sim <= self_sim


def test_css_mirror_similarity_symmetric():
    circle = _circle_contour(128, radius=5.0)
    vec = css_to_feature_vector(curvature_scale_space(circle, n_sigmas=5), n_bins=32)
    assert css_similarity_mirror(vec, vec) >= 0.98


def test_freeman_chain_code_length_matches_segments():
    # Image coordinates: y increases downward. Moving east then south.
    pts = np.array([[0, 0], [1, 0], [2, 0], [2, 1], [2, 2]])
    code = freeman_chain_code(pts)
    assert code == "0066"  # E E S S (image coords)


def test_fractal_motion_wound_shape_similarity():
    ana = FractalMotionAnalyzer()
    circle = _circle_contour(128, radius=10.0)
    vec = ana.wound_shape_vector(circle, n_sigmas=5, n_bins=32)
    assert vec.shape == (5 * 32,)
    assert ana.wound_shape_similarity(vec, vec) >= 0.98


def test_fractal_motion_chest_motion_bounded():
    ana = FractalMotionAnalyzer()
    noisy = [(i % 7) * 0.1 for i in range(64)]
    v = ana.chest_motion_fd(noisy)
    assert 0.0 <= v <= 1.0
