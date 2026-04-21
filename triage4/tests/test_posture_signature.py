from triage4.perception.body_regions import BodyRegionPolygonizer
from triage4.signatures import PostureSignatureExtractor


def _standing_regions():
    return BodyRegionPolygonizer().build_from_bbox([0, 0, 10, 30])


def _collapsed_regions():
    # Wider than tall — lying down silhouette.
    return BodyRegionPolygonizer().build_from_bbox([0, 0, 30, 10])


def test_posture_missing_regions_returns_zeros():
    result = PostureSignatureExtractor().extract({"head": []})
    assert result["posture_instability_score"] == 0.0
    assert result["quality_score"] == 0.0


def test_posture_standing_is_stable():
    regions = _standing_regions()
    result = PostureSignatureExtractor().extract(regions)
    assert result["posture_instability_score"] < 0.3
    assert result["collapse_score"] == 0.0
    assert result["quality_score"] > 0.0


def test_posture_collapsed_is_unstable():
    standing = PostureSignatureExtractor().extract(_standing_regions())
    collapsed = PostureSignatureExtractor().extract(_collapsed_regions())
    assert collapsed["collapse_score"] > standing["collapse_score"]
    assert collapsed["posture_instability_score"] >= standing["posture_instability_score"]


def test_posture_scores_in_unit_range():
    result = PostureSignatureExtractor().extract(_standing_regions())
    for key in (
        "posture_instability_score",
        "asymmetry_score",
        "collapse_score",
        "quality_score",
    ):
        assert 0.0 <= result[key] <= 1.0
