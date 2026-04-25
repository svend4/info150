"""Sea-lice burden signature.

Confidence-weighted average of upstream visual classifier
outputs. Returns unit-interval safety where 1.0 = no
detected burden, 0.0 = sustained high lice signature.

Norway, Scotland, and Chile all enforce regulatory caps
on sea-lice density (e.g. Norway 0.2 adult female lice
per fish during spring smolt migration); the library
flags BURDEN signals for vet review, never recommends
the regulatory + therapeutic response.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import SeaLiceSample


SIGNATURE_VERSION = "sea_lice_burden@1.0.0"


def compute_sea_lice_safety(
    samples: Iterable[SeaLiceSample],
) -> float:
    """Return sea-lice burden safety in [0, 1]."""
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    # Confidence-weighted mean of count_proxy.
    weighted_sum = 0.0
    total_weight = 0.0
    for s in sample_list:
        if s.classifier_confidence < 0.30:
            continue
        weighted_sum += s.count_proxy * s.classifier_confidence
        total_weight += s.classifier_confidence

    if total_weight == 0:
        return 1.0

    burden = weighted_sum / total_weight
    # burden 0 → 1.0, burden 1.0 → 0.
    return max(0.0, min(1.0, 1.0 - burden))
