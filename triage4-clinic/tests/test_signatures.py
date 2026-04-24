"""Tests for the four telemedicine-pre-screening signatures."""

from __future__ import annotations

from triage4_clinic.core.models import (
    AcousticSample,
    CoughSample,
    PostureSample,
    VitalsSample,
)
from triage4_clinic.signatures.acoustic_strain import compute_acoustic
from triage4_clinic.signatures.cardiac_readings import compute_cardiac
from triage4_clinic.signatures.postural_stability import compute_postural
from triage4_clinic.signatures.respiratory_readings import compute_respiratory


# ---------------------------------------------------------------------------
# cardiac_readings
# ---------------------------------------------------------------------------


def test_cardiac_empty_returns_neutral_no_alternatives():
    reading, alts = compute_cardiac([])
    assert reading.channel == "cardiac"
    assert reading.value == 1.0
    assert reading.signature_version  # non-empty
    assert alts == ()


def test_cardiac_unreliable_only_returns_neutral():
    samples = [
        VitalsSample(t_s=i, hr_bpm=140, rr_bpm=20, reliable=False)
        for i in range(5)
    ]
    reading, alts = compute_cardiac(samples)
    assert reading.value == 1.0
    assert alts == ()


def test_cardiac_in_band_returns_one_no_alternatives():
    samples = [
        VitalsSample(t_s=i, hr_bpm=72, rr_bpm=16, reliable=True)
        for i in range(5)
    ]
    reading, alts = compute_cardiac(samples)
    assert reading.value == 1.0
    assert alts == ()


def test_cardiac_elevated_returns_low_score_with_alternatives():
    samples = [
        VitalsSample(t_s=i, hr_bpm=135, rr_bpm=16, reliable=True)
        for i in range(5)
    ]
    reading, alts = compute_cardiac(samples)
    assert reading.value < 0.2
    # Elevated readings must produce grounded alternatives.
    assert len(alts) >= 3
    # At least one alt mentions exertion / anxiety / cardiac.
    texts = " ".join(a.text for a in alts).lower()
    assert "exertion" in texts or "anxiety" in texts
    assert "cardiac" in texts


def test_cardiac_above_high_cap_is_zero():
    samples = [
        VitalsSample(t_s=i, hr_bpm=150, rr_bpm=16, reliable=True)
        for i in range(5)
    ]
    reading, _ = compute_cardiac(samples)
    assert reading.value == 0.0


def test_cardiac_bradycardia_returns_alternatives_too():
    samples = [
        VitalsSample(t_s=i, hr_bpm=45, rr_bpm=16, reliable=True)
        for i in range(5)
    ]
    reading, alts = compute_cardiac(samples)
    assert reading.value < 1.0
    # Bradycardia-specific alternatives should include
    # athletic-fitness / medication framing.
    texts = " ".join(a.text for a in alts).lower()
    assert "athlete" in texts or "medication" in texts


# ---------------------------------------------------------------------------
# respiratory_readings
# ---------------------------------------------------------------------------


def test_respiratory_empty_returns_one():
    reading, alts = compute_respiratory([], [], 60.0)
    assert reading.value == 1.0
    assert alts == ()


def test_respiratory_in_band_no_coughs_returns_one():
    samples = [
        VitalsSample(t_s=i, hr_bpm=72, rr_bpm=16, reliable=True)
        for i in range(5)
    ]
    reading, alts = compute_respiratory(samples, [], 60.0)
    assert reading.value == 1.0
    assert alts == ()


def test_respiratory_elevated_rr_returns_alternatives():
    samples = [
        VitalsSample(t_s=i, hr_bpm=72, rr_bpm=32, reliable=True)
        for i in range(5)
    ]
    reading, alts = compute_respiratory(samples, [], 60.0)
    assert reading.value < 1.0
    assert len(alts) >= 1
    texts = " ".join(a.text for a in alts).lower()
    assert "exertion" in texts or "anxiety" in texts


def test_respiratory_cough_only_drops_score():
    samples = [
        VitalsSample(t_s=i, hr_bpm=72, rr_bpm=16, reliable=True)
        for i in range(5)
    ]
    # 6 coughs in 60 s = 6/min → cough_score = 0.
    coughs = [
        CoughSample(t_s=i * 10, confidence=0.8)
        for i in range(6)
    ]
    reading, alts = compute_respiratory(samples, coughs, 60.0)
    # Cough alone drives the channel to 0 even with RR in band.
    assert reading.value == 0.0
    # Cough alternatives mention upper-respiratory / allergic.
    texts = " ".join(a.text for a in alts).lower()
    assert "upper-respiratory" in texts or "allergic" in texts


def test_respiratory_low_confidence_coughs_ignored():
    samples = [
        VitalsSample(t_s=i, hr_bpm=72, rr_bpm=16, reliable=True)
        for i in range(5)
    ]
    coughs = [CoughSample(t_s=i * 10, confidence=0.3) for i in range(6)]
    reading, _ = compute_respiratory(samples, coughs, 60.0)
    assert reading.value == 1.0


# ---------------------------------------------------------------------------
# acoustic_strain
# ---------------------------------------------------------------------------


def test_acoustic_empty_returns_one():
    reading, alts = compute_acoustic([])
    assert reading.value == 1.0
    assert alts == ()


def test_acoustic_effortless_voice_returns_one():
    samples = [
        AcousticSample(t_s=i, strain_score=0.1, clarity=0.9)
        for i in range(5)
    ]
    reading, alts = compute_acoustic(samples)
    assert reading.value >= 0.85
    assert alts == ()


def test_acoustic_strained_voice_returns_alternatives():
    samples = [
        AcousticSample(t_s=i, strain_score=0.7, clarity=0.9)
        for i in range(5)
    ]
    reading, alts = compute_acoustic(samples)
    assert reading.value < 0.7
    assert len(alts) >= 3
    texts = " ".join(a.text for a in alts).lower()
    assert "overuse" in texts or "dehydration" in texts


def test_acoustic_low_clarity_samples_filtered():
    """Samples below clarity threshold should be dropped from
    the mean — otherwise a noisy clip tanks the score
    artificially."""
    samples = [
        AcousticSample(t_s=i, strain_score=0.9, clarity=0.1)
        for i in range(5)
    ]
    reading, _ = compute_acoustic(samples)
    # All below threshold → treated as empty → returns 1.0.
    assert reading.value == 1.0


# ---------------------------------------------------------------------------
# postural_stability
# ---------------------------------------------------------------------------


def test_postural_empty_returns_one():
    reading, alts = compute_postural([])
    assert reading.value == 1.0
    assert alts == ()


def test_postural_steady_returns_one():
    samples = [
        PostureSample(t_s=i, sway_magnitude=0.1, balance_steadiness=0.95)
        for i in range(5)
    ]
    reading, alts = compute_postural(samples)
    assert reading.value >= 0.9
    assert alts == ()


def test_postural_unstable_returns_alternatives():
    samples = [
        PostureSample(t_s=i, sway_magnitude=0.7, balance_steadiness=0.2)
        for i in range(5)
    ]
    reading, alts = compute_postural(samples)
    assert reading.value < 0.5
    assert len(alts) >= 3
    texts = " ".join(a.text for a in alts).lower()
    assert "fatigue" in texts or "vestibular" in texts or "medication" in texts


# ---------------------------------------------------------------------------
# Signature versioning is part of every reading
# ---------------------------------------------------------------------------


def test_all_signatures_tag_version():
    """Audit requirement: every reading carries a non-empty
    signature_version. This is enforced at construction, but
    test the expected format across all four signatures."""
    card, _ = compute_cardiac([])
    resp, _ = compute_respiratory([], [], 60.0)
    acou, _ = compute_acoustic([])
    post, _ = compute_postural([])
    for reading, expected_prefix in [
        (card, "cardiac_readings@"),
        (resp, "respiratory_readings@"),
        (acou, "acoustic_strain@"),
        (post, "postural_stability@"),
    ]:
        assert reading.signature_version.startswith(expected_prefix)
