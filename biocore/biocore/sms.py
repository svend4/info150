"""SMS-length structural cap for bandwidth-constrained handoff.

triage4-wild and triage4-bird both run their handoff over
Iridium satcom or low-bandwidth SMS. Both cap alert text
at 200 characters and raise ``ValueError`` if a longer
text is constructed. Identical shape, identical default
constant — extraction threshold met.

triage4-fish sends to a farm-management dashboard
(no SMS bandwidth issue) and does not use this helper;
it's an opt-in utility.
"""

from __future__ import annotations


# Standard SMS / Iridium frame budget. Consumer apps that
# adopt biocore for SMS-style handoff use this constant; if
# they need a different cap they pass it explicitly to
# ``check_sms_cap``.
DEFAULT_SMS_CAP_CHARS: int = 200


def check_sms_cap(
    text: str,
    max_chars: int = DEFAULT_SMS_CAP_CHARS,
    docs_pointer: str = "docs/PHILOSOPHY.md",
) -> None:
    """Raise ``ValueError`` if ``text`` exceeds ``max_chars``.

    Truncation downstream can silently drop the alert
    kind / level / location handle, changing the alert's
    meaning. Refusing oversized text at construction is
    safer than accepting a value that downstream code
    will mangle.
    """
    if len(text) > max_chars:
        raise ValueError(
            f"alert text exceeds SMS cap of {max_chars} chars "
            f"(got {len(text)}); see {docs_pointer}"
        )


__all__ = ["DEFAULT_SMS_CAP_CHARS", "check_sms_cap"]
