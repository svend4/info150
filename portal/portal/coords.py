"""6-bit domain coordinates with Hamming-distance proximity.

Each sibling is assigned a 6-bit tag along six orthogonal
axes:

    bit 0 (LSB): animal-wild         (untamed fauna)
    bit 1:        animal-managed      (livestock / pets / aquaculture)
    bit 2:        human-individual    (clinical / fitness / sport)
    bit 3:        human-collective    (crowd / disaster / elderly home)
    bit 4:        industrial-workplace(site / farm / driver-cab)
    bit 5 (MSB): environmental       (water / habitat / weather)

Hamming distance between two siblings' tags approximates
their domain proximity. Hamming-0 = same domain bucket
(e.g. ``triage4-bird`` and ``triage4-wild`` are both
wild-animal + environmental, distance 0). Hamming-1 = one
axis apart.

Why 6 bits and not embeddings: the catalog has ≤ 16
siblings and the axes are concrete domain choices, not
learned features. The coordinate system stays
human-auditable.
"""

from __future__ import annotations

# Bit positions (LSB first).
ANIMAL_WILD: int = 1 << 0
ANIMAL_MANAGED: int = 1 << 1
HUMAN_INDIVIDUAL: int = 1 << 2
HUMAN_COLLECTIVE: int = 1 << 3
INDUSTRIAL_WORKPLACE: int = 1 << 4
ENVIRONMENTAL: int = 1 << 5

ALL_AXES: tuple[tuple[str, int], ...] = (
    ("animal_wild",          ANIMAL_WILD),
    ("animal_managed",       ANIMAL_MANAGED),
    ("human_individual",     HUMAN_INDIVIDUAL),
    ("human_collective",     HUMAN_COLLECTIVE),
    ("industrial_workplace", INDUSTRIAL_WORKPLACE),
    ("environmental",        ENVIRONMENTAL),
)


# Per-sibling assignments. Only the three pilot siblings
# are populated initially; others can be added voluntarily
# when their adapters land.
SIBLING_COORDS: dict[str, int] = {
    "triage4-wild":   ANIMAL_WILD | ENVIRONMENTAL,
    "triage4-bird":   ANIMAL_WILD | ENVIRONMENTAL,
    "triage4-fish":   ANIMAL_MANAGED | INDUSTRIAL_WORKPLACE | ENVIRONMENTAL,
}


def hamming(a: int, b: int) -> int:
    """Population count of XOR — the Hamming distance.

    Both inputs are masked to 6 bits before counting so
    callers cannot widen the coordinate space by accident.
    """
    mask = (1 << 6) - 1
    return ((a & mask) ^ (b & mask)).bit_count()


def coord_for(sibling_id: str) -> int:
    """Lookup; raises ``KeyError`` for unknown siblings.

    Adapters do NOT call this — they only emit the
    sibling_id string. The discovery layer resolves the
    coordinate when computing domain neighbourhood.
    """
    if sibling_id not in SIBLING_COORDS:
        raise KeyError(
            f"sibling_id {sibling_id!r} has no coordinate "
            f"registered — add it to portal.coords.SIBLING_COORDS"
        )
    return SIBLING_COORDS[sibling_id]


def axes_set(coord: int) -> tuple[str, ...]:
    """Return the names of axes set in ``coord``.

    Useful for human-readable bridge evidence.
    """
    mask = (1 << 6) - 1
    return tuple(name for name, bit in ALL_AXES if (coord & mask) & bit)


__all__ = [
    "ALL_AXES",
    "ANIMAL_MANAGED",
    "ANIMAL_WILD",
    "ENVIRONMENTAL",
    "HUMAN_COLLECTIVE",
    "HUMAN_INDIVIDUAL",
    "INDUSTRIAL_WORKPLACE",
    "SIBLING_COORDS",
    "axes_set",
    "coord_for",
    "hamming",
]
