import pytest

from triage4.core.models import CasualtySignature
from triage4.triage_reasoning import UncertaintyModel, UncertaintyReport


def _sig_with_quality(quality: dict[str, float], visibility: float = 1.0) -> CasualtySignature:
    return CasualtySignature(
        visibility_score=visibility,
        raw_features=dict(quality),
    )


def test_uncertainty_high_quality_high_confidence():
    sig = _sig_with_quality(
        {
            "breathing_quality": 0.95,
            "perfusion_quality": 0.9,
            "bleeding_confidence": 0.95,
            "thermal_quality": 0.9,
        }
    )
    report = UncertaintyModel().from_signature(sig, base_score=0.8)
    assert isinstance(report, UncertaintyReport)
    assert report.overall_confidence > 0.8
    assert report.overall_uncertainty < 0.2


def test_uncertainty_low_quality_low_confidence():
    sig = _sig_with_quality(
        {
            "breathing_quality": 0.1,
            "perfusion_quality": 0.1,
            "bleeding_confidence": 0.1,
            "thermal_quality": 0.1,
        }
    )
    report = UncertaintyModel().from_signature(sig, base_score=0.8)
    assert report.overall_confidence < 0.5
    assert report.adjusted_score < 0.5


def test_uncertainty_visibility_discounts_confidence():
    high_vis = UncertaintyModel().from_signature(
        _sig_with_quality({"breathing_quality": 0.9}, visibility=1.0), 0.8
    )
    low_vis = UncertaintyModel().from_signature(
        _sig_with_quality({"breathing_quality": 0.9}, visibility=0.0), 0.8
    )
    assert high_vis.overall_confidence > low_vis.overall_confidence


def test_uncertainty_no_raw_features_uses_prior():
    report = UncertaintyModel().from_signature(
        CasualtySignature(visibility_score=1.0), base_score=0.7
    )
    # Prior confidence is 0.5 * visibility_adjustment.
    assert 0.3 < report.overall_confidence < 0.7


def test_uncertainty_all_values_in_unit_range():
    report = UncertaintyModel().from_signature(
        _sig_with_quality({"breathing_quality": 0.5}), 0.5
    )
    for name in (
        "base_score",
        "overall_confidence",
        "overall_uncertainty",
        "adjusted_score",
    ):
        val = getattr(report, name)
        assert 0.0 <= val <= 1.0


def test_uncertainty_rejects_out_of_range_inputs():
    with pytest.raises(ValueError):
        UncertaintyReport(
            base_score=1.2,
            overall_confidence=0.5,
            overall_uncertainty=0.5,
            adjusted_score=0.5,
        )
