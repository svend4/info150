"""Tests for eye / gaze / posture signatures."""

from __future__ import annotations

from triage4_drive.core.models import (
    EyeStateSample,
    GazeSample,
    PostureSample,
)
from triage4_drive.signatures.eye_closure import (
    compute_perclos,
    count_microsleeps,
)
from triage4_drive.signatures.gaze_deviation import compute_distraction_index
from triage4_drive.signatures.postural_tone import compute_postural_tone_score


# ---------------------------------------------------------------------------
# compute_perclos
# ---------------------------------------------------------------------------


def test_perclos_empty_returns_zero():
    assert compute_perclos([]) == 0.0


def test_perclos_all_open():
    samples = [EyeStateSample(t_s=i * 0.1, closure=0.1) for i in range(10)]
    assert compute_perclos(samples) == 0.0


def test_perclos_all_closed():
    samples = [EyeStateSample(t_s=i * 0.1, closure=0.95) for i in range(10)]
    assert compute_perclos(samples) == 1.0


def test_perclos_half_closed():
    samples = [
        EyeStateSample(t_s=i * 0.1, closure=0.95 if i % 2 else 0.1)
        for i in range(10)
    ]
    assert compute_perclos(samples) == 0.5


def test_perclos_boundary_p80():
    # Exactly 0.8 counts as closed.
    samples = [EyeStateSample(t_s=0.0, closure=0.8),
               EyeStateSample(t_s=0.1, closure=0.79)]
    assert compute_perclos(samples) == 0.5


# ---------------------------------------------------------------------------
# count_microsleeps
# ---------------------------------------------------------------------------


def test_microsleeps_empty_returns_zero():
    assert count_microsleeps([]) == 0


def test_microsleeps_short_blink_does_not_count():
    # Closed for 0.2 s — below the 0.5 s minimum.
    samples = [
        EyeStateSample(t_s=0.0, closure=0.1),
        EyeStateSample(t_s=0.1, closure=0.95),
        EyeStateSample(t_s=0.2, closure=0.95),
        EyeStateSample(t_s=0.3, closure=0.1),
    ]
    assert count_microsleeps(samples) == 0


def test_microsleeps_long_closure_counts():
    # Closed for 1.0 s — well past the 0.5 s minimum.
    samples = [
        EyeStateSample(t_s=0.0, closure=0.1),
        EyeStateSample(t_s=0.2, closure=0.95),
        EyeStateSample(t_s=0.5, closure=0.95),
        EyeStateSample(t_s=1.2, closure=0.95),
        EyeStateSample(t_s=1.3, closure=0.1),
    ]
    assert count_microsleeps(samples) == 1


def test_microsleeps_multiple_events():
    samples = [
        EyeStateSample(t_s=0.0, closure=0.1),
        EyeStateSample(t_s=0.5, closure=0.95),
        EyeStateSample(t_s=1.2, closure=0.95),
        EyeStateSample(t_s=1.5, closure=0.1),
        EyeStateSample(t_s=2.0, closure=0.95),
        EyeStateSample(t_s=2.8, closure=0.95),
        EyeStateSample(t_s=3.0, closure=0.1),
    ]
    assert count_microsleeps(samples) == 2


def test_microsleeps_unterminated_run_counts():
    # Eyes still closed at the end of the window.
    samples = [
        EyeStateSample(t_s=0.0, closure=0.1),
        EyeStateSample(t_s=0.5, closure=0.95),
        EyeStateSample(t_s=1.5, closure=0.95),
    ]
    assert count_microsleeps(samples) == 1


# ---------------------------------------------------------------------------
# compute_distraction_index
# ---------------------------------------------------------------------------


def test_distraction_empty_returns_zero():
    assert compute_distraction_index([]) == 0.0


def test_distraction_all_on_road():
    samples = [GazeSample(t_s=i * 0.2, region="road") for i in range(10)]
    assert compute_distraction_index(samples) == 0.0


def test_distraction_mirror_glances_are_on_task():
    samples = [
        GazeSample(t_s=0.0, region="road"),
        GazeSample(t_s=0.5, region="left_mirror"),
        GazeSample(t_s=1.0, region="road"),
        GazeSample(t_s=1.5, region="rearview_mirror"),
        GazeSample(t_s=2.0, region="road"),
    ]
    assert compute_distraction_index(samples) == 0.0


def test_distraction_off_road_drives_up():
    samples = [
        GazeSample(t_s=0.0, region="road"),
        GazeSample(t_s=1.0, region="off_road"),
        GazeSample(t_s=2.0, region="off_road"),
        GazeSample(t_s=3.0, region="road"),
    ]
    idx = compute_distraction_index(samples)
    # From t=1 to t=3 was off-road (2 s of 3 s total).
    assert 0.5 < idx <= 1.0


def test_distraction_dashboard_grace_window():
    # Brief dashboard glance well under 0.5 s — shouldn't count.
    samples = [
        GazeSample(t_s=0.0, region="road"),
        GazeSample(t_s=0.2, region="dashboard"),
        GazeSample(t_s=0.4, region="road"),
        GazeSample(t_s=2.0, region="road"),
    ]
    assert compute_distraction_index(samples) == 0.0


def test_distraction_long_dashboard_stare_counts():
    # Dashboard stare of ~2 s → ~1.5 s off-task after grace.
    samples = [
        GazeSample(t_s=0.0, region="road"),
        GazeSample(t_s=1.0, region="dashboard"),
        GazeSample(t_s=3.0, region="road"),
    ]
    idx = compute_distraction_index(samples)
    assert idx > 0.3


# ---------------------------------------------------------------------------
# compute_postural_tone_score
# ---------------------------------------------------------------------------


def test_postural_tone_upright_scores_zero():
    samples = [
        PostureSample(t_s=i * 0.5, nose_y=0.30, shoulder_midline_y=0.45)
        for i in range(10)
    ]
    assert compute_postural_tone_score(samples) == 0.0


def test_postural_tone_severe_drop_sustained_scores_one():
    # Nose at 0.70, shoulders at 0.45 → drop of 0.25 > 0.15
    # severe threshold, held for the full 5 s > 2 s hold.
    samples = [
        PostureSample(t_s=i * 0.5, nose_y=0.70, shoulder_midline_y=0.45)
        for i in range(10)
    ]
    assert compute_postural_tone_score(samples) == 1.0


def test_postural_tone_brief_drop_partial_score():
    # Severe drop held for ~1.5 s — shorter than the 2.0 s hold
    # threshold, so the score is partial rather than 1.0.
    samples = [
        PostureSample(t_s=0.0, nose_y=0.30, shoulder_midline_y=0.45),
        PostureSample(t_s=0.5, nose_y=0.70, shoulder_midline_y=0.45),
        PostureSample(t_s=1.0, nose_y=0.70, shoulder_midline_y=0.45),
        PostureSample(t_s=1.5, nose_y=0.70, shoulder_midline_y=0.45),
        PostureSample(t_s=2.0, nose_y=0.30, shoulder_midline_y=0.45),
    ]
    score = compute_postural_tone_score(samples)
    assert 0.0 < score < 1.0


def test_postural_tone_empty_returns_zero():
    assert compute_postural_tone_score([]) == 0.0


def test_postural_tone_mild_drop_scores_low():
    # Drop of 0.07 — above mild (0.05) but below severe (0.15).
    samples = [
        PostureSample(t_s=i * 0.5, nose_y=0.37, shoulder_midline_y=0.30)
        for i in range(10)
    ]
    score = compute_postural_tone_score(samples)
    assert 0.0 < score < 0.5
