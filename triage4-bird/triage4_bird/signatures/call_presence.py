"""Call-presence signature.

Reads ``CallSample`` records + the consumer-app-supplied
``expected_species`` list and returns a unit-interval
safety score for "calls present that should be present".

The signature does NOT reward confident identification of
unexpected species (a cuckoo where you don't expect one is
NOT inherently a problem); it only penalises absence of
expected species. Conservation-context judgement.

Returns 1.0 when every expected species appears with
reasonable confidence; lower when expected species are
absent.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import CallSample, Species


_MIN_CONFIDENT_CALLS = 1
_MIN_CONFIDENCE = 0.4


def compute_call_presence_safety(
    samples: Iterable[CallSample],
    expected_species: tuple[Species, ...],
) -> float:
    """Return call-presence safety score in [0, 1]."""
    if not expected_species:
        # No expectation supplied — call-presence channel is
        # neutral.
        return 1.0

    sample_list = list(samples)
    detected = {
        s.species for s in sample_list
        if s.confidence >= _MIN_CONFIDENCE
    }
    expected = set(expected_species)

    detected_expected = expected.intersection(detected)
    if not expected:
        return 1.0
    fraction_present = len(detected_expected) / len(expected)
    # Soften the penalty: detection rate 1.0 → safety 1.0,
    # detection rate 0.0 → safety 0.5 (absence of calls
    # alone isn't a hard urgent signal — birds are quiet
    # for many reasons).
    return max(0.0, min(1.0, 0.5 + 0.5 * fraction_present))


# Silence unused-import warning if needed — _MIN_CONFIDENT_CALLS
# is reserved for a future "minimum N calls per species"
# tightening of the signature.
_ = _MIN_CONFIDENT_CALLS
