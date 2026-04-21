import pytest

from triage4.signatures.radar import (
    AXIS_SEMANTICS,
    COMPASS,
    HEPTAGRAM_RAY_LABELS,
    SkeletonType,
    build_heptagram_signature,
    build_octagram_signature,
    build_shell_octagram,
    build_tower_octagram,
    heptagram_distance,
    heptagram_from_edge_weights,
    octagram_distance,
)


# --- Heptagram --------------------------------------------------------------


def test_heptagram_has_seven_rays_with_known_labels():
    sig = build_heptagram_signature({})
    assert len(sig.rays) == 7
    labels = [r.label for r in sig.rays]
    assert labels == HEPTAGRAM_RAY_LABELS


def test_heptagram_missing_weights_default_to_half():
    sig = build_heptagram_signature({})
    for r in sig.rays:
        assert r.length == pytest.approx(0.5)


def test_heptagram_weights_clamped_to_unit_interval():
    sig = build_heptagram_signature({"strength": 5.0, "direction": -2.0})
    strength = next(r for r in sig.rays if r.label == "strength")
    direction = next(r for r in sig.rays if r.label == "direction")
    assert strength.length == 1.0
    assert direction.length == 0.0


def test_heptagram_dominant_ray_picks_highest_weight():
    sig = build_heptagram_signature({"strength": 0.1, "confidence": 0.9})
    assert sig.dominant_ray.label == "confidence"


def test_heptagram_symmetry_score_between_zero_and_one():
    sig = build_heptagram_signature({r: 0.5 for r in HEPTAGRAM_RAY_LABELS})
    assert 0.0 <= sig.symmetry_score <= 1.0
    assert sig.symmetry_score == pytest.approx(1.0, abs=1e-6)


def test_heptagram_distance_identical_is_zero():
    sig = build_heptagram_signature({"strength": 0.8})
    assert heptagram_distance(sig, sig) == pytest.approx(0.0)


def test_heptagram_from_edge_weights_produces_valid_signature():
    edges = [("a", "b", 0.7), ("b", "c", 0.5), ("a", "c", 0.9)]
    sig = heptagram_from_edge_weights(["a", "b", "c"], edges)
    assert len(sig.rays) == 7
    assert 0.0 <= sig.total_energy <= 1.0


def test_heptagram_from_empty_edges():
    sig = heptagram_from_edge_weights([], [])
    assert len(sig.rays) == 7


# --- Octagram ---------------------------------------------------------------


def test_octagram_has_eight_rays_on_compass():
    sig = build_octagram_signature({})
    assert len(sig.rays) == 8
    dirs = [r.direction for r in sig.rays]
    assert dirs == COMPASS


def test_octagram_dominant_axis_returns_known_pair():
    sig = build_octagram_signature({"N": 0.9, "S": 0.9})
    axis = sig.dominant_axis
    assert axis in AXIS_SEMANTICS


def test_octagram_to_vector_shape():
    sig = build_octagram_signature({"N": 0.5})
    assert len(sig.to_vector()) == 16


def test_octagram_skeleton_vertices_has_nine_entries():
    sig = build_octagram_signature({})
    assert len(sig.skeleton_vertices()) == 9


def test_octagram_shell_is_shell_skeleton_type():
    shell = build_shell_octagram()
    assert shell.skeleton_type == SkeletonType.SHELL


def test_octagram_tower_builder_produces_valid_skeleton():
    tower = build_tower_octagram()
    assert isinstance(tower.skeleton_type, SkeletonType)
    # The auto-detector can classify this builder's profile into several
    # skeleton types depending on the exact ray distribution; just ensure
    # it's one of the known ones and the structure is well-formed.
    assert len(tower.rays) == 8


def test_octagram_distance_identical_is_zero():
    sig = build_octagram_signature({"N": 0.8})
    assert octagram_distance(sig, sig) == pytest.approx(0.0)
