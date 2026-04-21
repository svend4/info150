import numpy as np
import pytest

from triage4.matching.geometric_match import (
    area_ratio_similarity,
    aspect_ratio_similarity,
    batch_geometry_match,
    compute_geometry_from_contour,
    edge_length_similarity,
    hu_moments_similarity,
    match_geometry,
)


def _square(side: float = 10.0, n: int = 40) -> np.ndarray:
    per = n // 4
    t = np.linspace(0, 1, per, endpoint=False)
    top = np.column_stack([t * side, np.zeros_like(t)])
    right = np.column_stack([np.full_like(t, side), t * side])
    bottom = np.column_stack([side - t * side, np.full_like(t, side)])
    left = np.column_stack([np.zeros_like(t), side - t * side])
    return np.vstack([top, right, bottom, left])


def _rectangle(w: float, h: float, n: int = 40) -> np.ndarray:
    per = n // 4
    t = np.linspace(0, 1, per, endpoint=False)
    top = np.column_stack([t * w, np.zeros_like(t)])
    right = np.column_stack([np.full_like(t, w), t * h])
    bottom = np.column_stack([w - t * w, np.full_like(t, h)])
    left = np.column_stack([np.zeros_like(t), h - t * h])
    return np.vstack([top, right, bottom, left])


def test_compute_geometry_for_square():
    g = compute_geometry_from_contour(_square(10.0))
    assert g.area > 0
    assert g.perimeter > 0
    assert g.hull_area >= g.area * 0.9
    assert g.aspect_ratio == pytest.approx(1.0, abs=1e-6)
    assert g.hu_moments.shape == (7,)
    assert g.bbox == (0, 0, 10, 10)


def test_compute_geometry_rejects_tiny_contour():
    g = compute_geometry_from_contour(np.array([[0.0, 0.0]]))
    assert g.area == 0.0
    assert g.perimeter == 0.0
    assert g.hu_moments.shape == (7,)


def test_aspect_ratio_similarity_identical():
    g = compute_geometry_from_contour(_square(10.0))
    assert aspect_ratio_similarity(g, g) == pytest.approx(1.0)


def test_area_ratio_similarity_scales_correctly():
    g_small = compute_geometry_from_contour(_square(5.0))
    g_big = compute_geometry_from_contour(_square(10.0))
    s = area_ratio_similarity(g_small, g_big)
    assert 0.0 <= s <= 1.0
    # small square is 1/4 the area of big → similarity ~0.25
    assert s == pytest.approx(0.25, abs=0.1)


def test_hu_moments_similarity_identical_is_one():
    g = compute_geometry_from_contour(_square(10.0))
    assert hu_moments_similarity(g, g) == pytest.approx(1.0)


def test_edge_length_similarity_ratio():
    assert edge_length_similarity(10.0, 10.0) == 1.0
    assert edge_length_similarity(5.0, 10.0) == 0.5
    assert edge_length_similarity(0.0, 0.0) == 1.0


def test_match_geometry_identical_is_near_one():
    g = compute_geometry_from_contour(_square(10.0))
    result = match_geometry(g, g)
    assert 0.99 <= result.score <= 1.0
    assert result.method == "geometric"


def test_match_geometry_rectangle_vs_square_lower():
    g_sq = compute_geometry_from_contour(_square(10.0))
    g_rect = compute_geometry_from_contour(_rectangle(20.0, 5.0))
    sim_self = match_geometry(g_sq, g_sq).score
    sim_cross = match_geometry(g_sq, g_rect).score
    assert sim_cross < sim_self


def test_batch_geometry_match_returns_list():
    shapes = [compute_geometry_from_contour(_square(10.0)) for _ in range(3)]
    results = batch_geometry_match(shapes, pairs=[(0, 1), (0, 2)])
    assert len(results) == 2
    for r in results:
        assert 0.0 <= r.score <= 1.0
