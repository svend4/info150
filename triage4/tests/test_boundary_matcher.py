import numpy as np
import pytest

from triage4.matching import (
    ShapeMatch,
    batch_match_boundaries,
    chamfer_distance,
    extract_boundary_points,
    frechet_approx,
    hausdorff_distance,
    match_boundary_pair,
    score_boundary_pair,
    shape_distances,
    shape_similarity,
)


def _rect_contour(w: float = 100.0, h: float = 60.0, n: int = 80) -> np.ndarray:
    per_side = n // 4
    t = np.linspace(0, 1, per_side, endpoint=False)
    top = np.column_stack([t * w, np.zeros_like(t)])
    right = np.column_stack([np.full_like(t, w), t * h])
    bottom = np.column_stack([w - t * w, np.full_like(t, h)])
    left = np.column_stack([np.zeros_like(t), h - t * h])
    return np.vstack([top, right, bottom, left])


def test_hausdorff_identical_is_zero():
    a = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])
    assert hausdorff_distance(a, a) == 0.0


def test_chamfer_identical_is_zero():
    a = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]])
    assert chamfer_distance(a, a) == 0.0


def test_frechet_nonnegative():
    a = np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]])
    b = np.array([[0.0, 1.0], [1.0, 1.0], [2.0, 1.0]])
    assert frechet_approx(a, b) >= 0.0


def test_all_distances_handle_empty():
    empty = np.zeros((0, 2))
    pts = np.array([[0.0, 0.0]])
    assert hausdorff_distance(empty, pts) == 0.0
    assert chamfer_distance(empty, pts) == 0.0
    assert frechet_approx(empty, pts) == 0.0


def test_shape_distances_returns_three_metrics():
    a = _rect_contour(10.0, 5.0, 40)
    b = _rect_contour(10.0, 5.0, 40)
    d = shape_distances(a, b)
    assert set(d) == {"hausdorff", "chamfer", "frechet"}
    for v in d.values():
        assert v >= 0.0


def test_shape_similarity_identical_is_near_one():
    a = _rect_contour(10.0, 5.0, 40)
    m = shape_similarity(a, a, max_dist=10.0)
    assert isinstance(m, ShapeMatch)
    assert m.total_score == pytest.approx(1.0, abs=1e-6)
    assert m.hausdorff == pytest.approx(1.0, abs=1e-6)


def test_shape_similarity_different_is_less():
    a = _rect_contour(10.0, 5.0, 40)
    b = _rect_contour(10.0, 5.0, 40) + np.array([[50.0, 50.0]])
    m = shape_similarity(a, b, max_dist=10.0)
    assert m.total_score < 0.5


def test_extract_boundary_points_rejects_invalid_side():
    with pytest.raises(ValueError):
        extract_boundary_points(_rect_contour(), side=9)


def test_match_boundary_pair_returns_boundary_match():
    r = _rect_contour()
    match = match_boundary_pair(r, r, idx1=0, idx2=1, side1=2, side2=0, max_dist=50.0)
    assert match.idx1 == 0 and match.idx2 == 1
    assert 0.0 <= match.total_score <= 1.0
    assert "n_points" in match.params


def test_batch_match_boundaries_smoke():
    shapes = [_rect_contour(w=10.0), _rect_contour(w=10.0), _rect_contour(w=20.0)]
    results = batch_match_boundaries(shapes, pairs=[(0, 1), (0, 2)])
    assert len(results) == 2
    for r in results:
        assert 0.0 <= r.total_score <= 1.0


def test_score_boundary_pair_respects_weights():
    a = _rect_contour()
    b = _rect_contour() + np.array([[5.0, 5.0]])
    # Only hausdorff weight — total should equal hausdorff score.
    h, c, f, total = score_boundary_pair(a, b, max_dist=50.0, weights=(1.0, 0.0, 0.0))
    assert total == pytest.approx(h, abs=1e-6)
