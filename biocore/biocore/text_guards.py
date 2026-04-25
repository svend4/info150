"""Generic claims-guard helpers.

Every claims-guard ``__post_init__`` across the fourteen
siblings follows the same shape:

1. Lower-case the alert text.
2. Walk a per-domain forbidden-vocabulary tuple.
3. If a phrase appears in the lowered text, raise
   ``ValueError`` with a consistent message format that
   names the offending phrase, the boundary list, and a
   pointer to ``docs/PHILOSOPHY.md``.

The vocabulary tuples themselves stay per-sibling — each
domain's list IS the boundary, and unifying them would
erase domain specificity. The CHECK SHAPE, however, is
identical across every dataclass that runs it.

Same idea for the ``athlete <firstname>`` /
``patient <firstname>`` / ``swimmer <firstname>``
identifier-prefix pattern: each sibling has its own
prefix list (the list of common first names matters less
than the prefix shape — ``role <name>``), but the check
itself is the same shape everywhere.
"""

from __future__ import annotations

from typing import Iterable


def check_forbidden_phrases(
    text: str,
    phrases: Iterable[str],
    list_label: str,
    docs_pointer: str = "docs/PHILOSOPHY.md",
) -> None:
    """Raise ``ValueError`` if ``text`` contains any
    forbidden phrase.

    The check is case-insensitive — ``text.lower()`` is
    matched against each phrase. Phrases are expected to
    be lower-case already.

    ``list_label`` is the per-list short tag the calling
    sibling uses (e.g. ``"clinical"``, ``"surveillance-
    overreach"``, ``"antibiotic-dosing-overreach"``). It
    appears in the error message so the failure points
    at the correct boundary list when an alert
    construction fails.
    """
    low = text.lower()
    for phrase in phrases:
        if phrase in low:
            raise ValueError(
                f"alert text contains forbidden {list_label} "
                f"phrase {phrase!r}; see {docs_pointer}"
            )


def check_identifier_prefix(
    text: str,
    prefixes: Iterable[str],
    list_label: str = "identification",
    docs_pointer: str = "docs/PHILOSOPHY.md",
) -> None:
    """Raise ``ValueError`` if ``text`` contains an
    identifier-style prefix pattern.

    Used for the ``role <firstname>`` heuristic shared
    across triage4-drive / triage4-home / triage4-site /
    triage4-aqua / triage4-pet / triage4-clinic /
    triage4-wild / triage4-bird / triage4-sport (the
    common-first-name prefix list is per-sibling; the
    check shape is shared).
    """
    low = text.lower()
    for prefix in prefixes:
        if prefix in low:
            raise ValueError(
                f"alert text appears to identify the subject "
                f"({prefix!r}; {list_label} boundary; see "
                f"{docs_pointer})"
            )


__all__ = ["check_forbidden_phrases", "check_identifier_prefix"]
