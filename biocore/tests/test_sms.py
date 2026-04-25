"""Tests for biocore.sms."""

from __future__ import annotations

import pytest

from biocore.sms import DEFAULT_SMS_CAP_CHARS, check_sms_cap


def test_default_cap_is_200():
    assert DEFAULT_SMS_CAP_CHARS == 200


def test_short_text_passes():
    check_sms_cap("URGENT (zone-A1): density elevated.")


def test_text_at_cap_passes():
    text = "X" * DEFAULT_SMS_CAP_CHARS
    check_sms_cap(text)


def test_text_exceeding_cap_raises():
    text = "X" * (DEFAULT_SMS_CAP_CHARS + 1)
    with pytest.raises(ValueError, match="SMS cap"):
        check_sms_cap(text)


def test_custom_cap():
    check_sms_cap("X" * 80, max_chars=80)
    with pytest.raises(ValueError, match="SMS cap of 80"):
        check_sms_cap("X" * 81, max_chars=80)


def test_error_message_includes_actual_length():
    try:
        check_sms_cap("X" * 250)
    except ValueError as e:
        assert "got 250" in str(e)


def test_error_message_includes_docs_pointer():
    try:
        check_sms_cap("X" * 250)
    except ValueError as e:
        assert "docs/PHILOSOPHY.md" in str(e)


def test_custom_docs_pointer():
    try:
        check_sms_cap("X" * 250, docs_pointer="docs/SMS_BUDGET.md")
    except ValueError as e:
        assert "docs/SMS_BUDGET.md" in str(e)


def test_empty_text_passes():
    """Empty text under cap — passes. The dataclass that
    calls this also enforces non-empty separately."""
    check_sms_cap("")
