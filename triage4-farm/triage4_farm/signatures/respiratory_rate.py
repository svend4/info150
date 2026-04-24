"""Stand-off respiratory welfare score from breaths-per-minute.

Per-species normal bands (loose, literature-derived placeholders):

- dairy cow: 20-40 bpm resting, 60 cap before the observation
  layer flags respiratory concern.
- pig (grower): 25-45 bpm resting, 70 cap.
- chicken (broiler): 20-40 bpm resting, 80 cap (they pant
  aggressively when heat-stressed).

Sources: MSD Veterinary Manual tables (vital signs by species),
2020 edition. These are OBSERVATION reference bands for a
welfare-watchdog tool — not clinical cut-offs, and definitely
not a diagnosis. See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from ..core.enums import Species


# (resting_low, resting_high, cap_bpm)
_BANDS: dict[Species, tuple[float, float, float]] = {
    "dairy_cow": (20, 40, 60),
    "pig": (25, 45, 70),
    "chicken": (20, 40, 80),
}


def _band_score(value: float, band: tuple[float, float, float]) -> float:
    """1.0 inside the resting band, linearly decaying to 0 at cap."""
    lo, hi, cap = band
    if value < lo:
        # Below the resting band — unusual (torpor / depressed
        # state) but still a welfare concern. Score linearly to
        # 0 at ``lo / 2``.
        if value <= lo / 2:
            return 0.0
        return (value - lo / 2) / (lo / 2)
    if value <= hi:
        return 1.0
    if value >= cap:
        return 0.0
    return 1.0 - (value - hi) / (cap - hi)


def compute_respiratory_score(
    respiratory_bpm: float | None,
    species: Species,
) -> float | None:
    """Return a respiratory welfare score in [0, 1], or None.

    Returns ``None`` if the respiratory rate is missing — the
    caller (welfare engine) treats "missing" as "no signal
    available", not "signal fine". That matters for the
    observation-only posture: we never fabricate wellness.
    """
    if respiratory_bpm is None:
        return None
    if species not in _BANDS:
        raise KeyError(f"no respiratory band for species {species!r}")
    return _band_score(float(respiratory_bpm), _BANDS[species])
