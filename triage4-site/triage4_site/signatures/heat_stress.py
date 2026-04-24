"""Heat-stress signature.

Combines two observable signals into a unit-interval
heat-safety score:

1. Skin-ambient differential — the body's thermal gradient.
   When skin temperature is elevated AND ambient is close to
   or above skin temp, evaporative cooling is compromised.
2. Recent movement slowdown — separate input from the
   fatigue-gait channel, optional here.

Thresholds come from ACGIH TLV heat-stress guidance and NIOSH
Criteria for a Recommended Standard: Occupational Exposure
to Heat and Hot Environments (2016). Protocol-authentic
defaults; real deployments calibrate against site-specific
workload and acclimatisation.

This is an OBSERVATION score. Never a clinical diagnosis
("heat stroke") — see docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from typing import Iterable

from ..core.models import ThermalSample


# Skin-temperature bands (°C). Resting-typical ~32-34;
# sustained working ~35-36; elevated stress threshold ~37.5;
# marked heat-stress ~38.5.
_SKIN_ELEVATED_C = 37.5
_SKIN_MARKED_C = 38.5

# Ambient-temperature cap. Beyond this the body's ability
# to shed heat drops sharply regardless of skin readings.
_AMBIENT_CAP_C = 35.0

# Skin-ambient differential threshold. Below this value
# evaporative cooling is compromised.
_DIFFERENTIAL_LOW_C = 2.0


def compute_heat_safety(
    samples: Iterable[ThermalSample],
) -> float:
    """Return heat-safety score in [0, 1].

    1.0 = no heat-stress signal. 0.0 = strong heat-stress
    signal (elevated skin + hot ambient + small differential).

    Empty input returns 1.0 — calibration alerts surface
    the lack-of-data separately.
    """
    sample_list = list(samples)
    if not sample_list:
        return 1.0

    worst = 1.0
    for s in sample_list:
        sample_score = _sample_score(s)
        worst = min(worst, sample_score)
    return worst


def _sample_score(s: ThermalSample) -> float:
    """Per-sample heat-safety score."""
    skin_score = 1.0
    if s.skin_temp_c >= _SKIN_MARKED_C:
        skin_score = 0.0
    elif s.skin_temp_c >= _SKIN_ELEVATED_C:
        span = _SKIN_MARKED_C - _SKIN_ELEVATED_C
        skin_score = 1.0 - (s.skin_temp_c - _SKIN_ELEVATED_C) / span

    ambient_score = 1.0
    if s.ambient_temp_c >= _AMBIENT_CAP_C:
        # Above the cap, partial credit that scales with
        # how far above.
        over = s.ambient_temp_c - _AMBIENT_CAP_C
        ambient_score = max(0.0, 1.0 - over / 10.0)

    differential = s.skin_temp_c - s.ambient_temp_c
    differential_score = 1.0
    if differential < _DIFFERENTIAL_LOW_C:
        # Shrinks to 0 as the differential closes / inverts.
        differential_score = max(
            0.0, min(1.0, (differential + 1.0) / (_DIFFERENTIAL_LOW_C + 1.0))
        )

    # Three-factor product — any single channel being at 0
    # drives the overall to 0, which matches the physics
    # (compromised cooling dominates no matter the source).
    return max(0.0, min(1.0, skin_score * ambient_score * differential_score))
