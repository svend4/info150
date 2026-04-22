"""Tests for scripts/claims_lint.py.

Ensures:
- the repo currently passes claims-lint (regression lock);
- known good phrasings do not trigger;
- known bad phrasings do trigger;
- the allowlist works (regulatory docs are exempt);
- inline `[claims-lint: allow]` marker works.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from claims_lint import _INLINE_ALLOW_MARKER, _scan_text, scan  # noqa: E402


# ---------------------------------------------------------------------------
# Whole-repo regression lock
# ---------------------------------------------------------------------------


def test_repo_passes_claims_lint():
    """The repo MUST pass claims-lint on every commit."""
    findings = scan()
    assert findings == [], "\n".join(f.format() for f in findings)


# ---------------------------------------------------------------------------
# Good phrasings (must NOT trigger)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "good",
    [
        "triage4 is a decision-support research tool.",
        "We treat the contour as a uniform curve.",
        "The mission is treated as a casualty (fractal symmetry).",
        "Treatment can be delayed without losing the patient — Larrey 1797.",
        "An immediate casualty was treated at t=42 in the synthetic scenario.",
        "Per-channel confidence surfaces quality degradation.",
        "Operator retains override on every recommendation.",
    ],
)
def test_good_phrasing_does_not_trigger(good, tmp_path):
    f = tmp_path / "doc.md"
    f.write_text(good, encoding="utf-8")
    findings = list(_scan_text(good, f))
    assert findings == [], [x.format() for x in findings]


# ---------------------------------------------------------------------------
# Bad phrasings (MUST trigger)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad,expected_term",
    [
        ("triage4 can diagnose hemorrhagic shock.", "diagnose"),
        ("The system is able to treat casualties remotely.", "product claim"),
        ("triage4 cures wounds via autonomous care.", "cure"),
        ("triage4 is a medical device.", "medical device"),
        ("This stack is FDA cleared.", "FDA-cleared"),
        ("Our software is FDA approved for triage.", "FDA-cleared"),
        ("This product is CE marked.", "CE-marked"),
        ("Clinically proven across 10,000 patients.", "clinically proven"),
        ("The system will treat patients autonomously.", "product claim"),
    ],
)
def test_bad_phrasing_triggers(bad, expected_term, tmp_path):
    f = tmp_path / "doc.md"
    f.write_text(bad, encoding="utf-8")
    findings = list(_scan_text(bad, f))
    assert findings, f"expected a finding for {bad!r}"
    assert any(x.term == expected_term for x in findings), (
        f"wanted {expected_term!r}, got {[x.term for x in findings]}"
    )


# ---------------------------------------------------------------------------
# Inline allow marker
# ---------------------------------------------------------------------------


def test_inline_allow_marker_suppresses_finding():
    line = f"triage4 can diagnose things.  {_INLINE_ALLOW_MARKER}"
    findings = list(_scan_text(line, Path("doc.md")))
    assert findings == []


def test_inline_allow_marker_is_precise():
    """The marker only suppresses the line it appears on."""
    text = (
        f"triage4 can diagnose things.  {_INLINE_ALLOW_MARKER}\n"
        "triage4 is FDA cleared.\n"
    )
    findings = list(_scan_text(text, Path("doc.md")))
    assert len(findings) == 1
    assert findings[0].term == "FDA-cleared"


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------


def test_regulatory_doc_is_allowlisted():
    """REGULATORY.md explicitly names the forbidden words — that MUST be
    allowed, or the regulatory-awareness doc can't exist."""
    # This is covered implicitly by test_repo_passes_claims_lint, but
    # surface it as a focused assertion too.
    reg = (_REPO_ROOT / "docs" / "REGULATORY.md").read_text(encoding="utf-8")
    assert "diagnose" in reg.lower() or "FDA" in reg
    # And yet the repo passes.
    assert scan() == []
