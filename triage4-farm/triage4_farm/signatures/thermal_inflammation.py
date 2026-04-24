"""Surface-temperature welfare score from a unit-free hotspot proxy.

Stand-off IR cameras (handheld or gantry) produce a focal-hotspot
intensity for each animal — a dimensionless number in [0, 1]
representing how much warmer the hottest patch on the animal is
versus its body baseline. That upstream computation is
out-of-scope for triage4-farm; this module consumes its output.

Intuition:
- 0.0 - 0.15: within natural variation across species + ambient
  conditions — score near 1.0.
- 0.15 - 0.40: elevated focal warmth — welfare-concern range.
- 0.40+: a pronounced local hotspot — vet review warranted.

This is an OBSERVATION score. It does not diagnose inflammation,
infection, or any specific condition. See docs/PHILOSOPHY.md.
"""

from __future__ import annotations


_NORMAL_CAP = 0.15
_CONCERN_CAP = 0.40


def compute_thermal_score(thermal_hotspot: float | None) -> float | None:
    """Return a thermal welfare score in [0, 1], or None.

    Returns ``None`` if no IR signal is provided — the welfare
    engine treats this as a missing channel and excludes it from
    the overall weighting.
    """
    if thermal_hotspot is None:
        return None
    if not 0.0 <= thermal_hotspot <= 1.0:
        raise ValueError(
            f"thermal_hotspot must be in [0, 1], got {thermal_hotspot}"
        )
    if thermal_hotspot <= _NORMAL_CAP:
        return 1.0
    if thermal_hotspot >= _CONCERN_CAP:
        # Beyond the concern cap, decay smoothly toward 0 as
        # hotspot goes to 1.0. Keeps the score monotone.
        span_above = 1.0 - _CONCERN_CAP
        over = thermal_hotspot - _CONCERN_CAP
        return max(0.0, 0.3 * (1.0 - over / span_above))
    # Linear decay from 1.0 at normal-cap to 0.3 at concern-cap.
    span = _CONCERN_CAP - _NORMAL_CAP
    into = thermal_hotspot - _NORMAL_CAP
    return 1.0 - 0.7 * (into / span)
