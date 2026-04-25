"""Tests for biocore.text_guards."""

from __future__ import annotations

import pytest

from biocore.text_guards import (
    check_forbidden_phrases,
    check_identifier_prefix,
)


# ---------------------------------------------------------------------------
# check_forbidden_phrases
# ---------------------------------------------------------------------------


def test_clean_text_passes():
    """Should not raise when no forbidden phrase present."""
    check_forbidden_phrases(
        text="Form asymmetry trending above baseline.",
        phrases=("predicts injury", "guaranteed safe"),
        list_label="injury-prediction-overreach",
    )


def test_forbidden_phrase_raises():
    with pytest.raises(ValueError, match="injury-prediction"):
        check_forbidden_phrases(
            text="The athlete will get injured next session.",
            phrases=("predicts injury", "will get injured"),
            list_label="injury-prediction-overreach",
        )


def test_check_is_case_insensitive():
    """Phrases stored lower-case; text lower-cased before
    matching. Capitalised text in the alert should still
    trigger the guard."""
    with pytest.raises(ValueError):
        check_forbidden_phrases(
            text="OUTBREAK DETECTED at zone-A1.",
            phrases=("outbreak detected",),
            list_label="surveillance-overreach",
        )


def test_phrase_substring_match():
    """Phrases match as substrings — 'no concerns' inside
    'no concerns this window' triggers."""
    with pytest.raises(ValueError):
        check_forbidden_phrases(
            text="No concerns this window for pen-A1.",
            phrases=("no concerns",),
            list_label="no-false-reassurance",
        )


def test_empty_phrases_passes():
    """Empty phrase list = no check, never raises."""
    check_forbidden_phrases(
        text="Anything goes.",
        phrases=(),
        list_label="empty",
    )


def test_first_match_wins():
    """When multiple phrases match, the FIRST in the
    iteration order is the one named in the error.
    Documented for callers that order their lists by
    severity."""
    try:
        check_forbidden_phrases(
            text="Outbreak detected and pandemic conditions.",
            phrases=("outbreak detected", "pandemic"),
            list_label="surveillance-overreach",
        )
    except ValueError as e:
        # Ordering matters — outbreak detected appears
        # first in the phrases tuple.
        assert "outbreak detected" in str(e)


def test_error_message_contains_phrase_and_label_and_pointer():
    try:
        check_forbidden_phrases(
            text="Predicts injury within two weeks.",
            phrases=("predicts injury",),
            list_label="injury-prediction-overreach",
            docs_pointer="docs/PHILOSOPHY.md",
        )
    except ValueError as e:
        msg = str(e)
        assert "predicts injury" in msg
        assert "injury-prediction-overreach" in msg
        assert "docs/PHILOSOPHY.md" in msg


def test_custom_docs_pointer_appears_in_message():
    try:
        check_forbidden_phrases(
            text="Outbreak detected.",
            phrases=("outbreak detected",),
            list_label="surveillance-overreach",
            docs_pointer="docs/POSTURE.md",
        )
    except ValueError as e:
        assert "docs/POSTURE.md" in str(e)


# ---------------------------------------------------------------------------
# check_identifier_prefix
# ---------------------------------------------------------------------------


def test_clean_text_passes_identifier_check():
    check_identifier_prefix(
        text="Athlete shows form asymmetry above baseline.",
        prefixes=("athlete john ", "player mike "),
    )


def test_identifier_prefix_raises():
    with pytest.raises(ValueError, match="identification"):
        check_identifier_prefix(
            text="Athlete John shows asymmetry.",
            prefixes=("athlete john ",),
        )


def test_identifier_prefix_case_insensitive():
    with pytest.raises(ValueError):
        check_identifier_prefix(
            text="ATHLETE JANE elevated load.",
            prefixes=("athlete jane ",),
        )


def test_identifier_prefix_custom_label():
    try:
        check_identifier_prefix(
            text="Patient Mary submitted clip.",
            prefixes=("patient mary ",),
            list_label="privacy",
        )
    except ValueError as e:
        assert "privacy" in str(e)


def test_identifier_prefix_error_includes_phrase_and_pointer():
    try:
        check_identifier_prefix(
            text="Driver John high PERCLOS.",
            prefixes=("driver john ",),
            list_label="privacy",
            docs_pointer="docs/PHILOSOPHY.md",
        )
    except ValueError as e:
        assert "driver john" in str(e)
        assert "privacy" in str(e)
        assert "docs/PHILOSOPHY.md" in str(e)
