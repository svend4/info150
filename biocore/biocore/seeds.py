"""Deterministic RNG seeding for synthetic-fixture generators.

Stdlib ``hash()`` on strings is randomised per-process by
default (PYTHONHASHSEED). Synthetic generators that derive
RNG seeds from string keys via ``hash()`` produce different
sequences across pytest invocations, which surfaces as
flaky tests near decision boundaries.

twelve of the fourteen triage4 siblings need this; the
helper is the same shape in each of them, hence
extraction.
"""

from __future__ import annotations

import zlib


def crc32_seed(*parts: object) -> int:
    """Return a deterministic 32-bit RNG seed from arbitrary parts.

    Each ``part`` is converted via ``str()`` and joined with
    a ``|`` separator. The result is a CRC-32 of the UTF-8
    encoding — stable across processes (unlike ``hash()``)
    and stable across Python versions (unlike a stdlib hash
    that may change implementation).

    Typical use::

        rng = random.Random(crc32_seed(observation_id, species, seed))

    The seed is in [0, 2**32 - 1], which fits ``random.Random``
    initialisation directly.
    """
    if not parts:
        raise ValueError("crc32_seed requires at least one part")
    joined = "|".join(str(p) for p in parts)
    return zlib.crc32(joined.encode("utf-8"))


__all__ = ["crc32_seed"]
