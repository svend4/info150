"""Common shape every adapter produces.

Three pieces:

- ``PortalEntry`` — the narrow value-object every adapter
  produces. Sibling-agnostic. Carries the fields needed for
  cross-sibling discovery (sibling id, kind, level, location,
  observed value, time window) plus a free-form ``payload``
  mapping for sibling-specific extras the discovery layer
  may consult opportunistically.
- ``BridgeKind`` — six curated relationship types. The
  number is deliberately small (the nautilus reference
  implementation has 33; experience inside info150 will
  decide which extras are worth the maintenance cost
  before we add more).
- ``Bridge`` — one typed edge between two ``PortalEntry``
  instances, with a free-form ``evidence`` string the
  discovery rule fills in for human inspection.

Naming convention: ``entry.entry_id`` is unique within
``entry.sibling_id`` only — the portal-wide unique key is
``(sibling_id, entry_id)``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class BridgeKind(str, Enum):
    """Curated cross-sibling relationship types.

    Six kinds initially. Each kind has one discovery rule
    (see ``portal.discovery``) so the registry never grows
    edges nobody can explain.
    """

    ANALOGY = "analogy"
    CO_OCCURRENCE = "co_occurrence"
    ESCALATION = "escalation"
    DOMAIN_NEIGHBOR = "domain_neighbor"
    GEOGRAPHIC_NEIGHBOR = "geographic_neighbor"
    TEMPORAL_CORRELATE = "temporal_correlate"


# Canonical three-tier vocabulary the portal speaks.
# Siblings keep their native labels — adapters translate
# at the boundary. Examples of native variants in the
# catalog today:
#   - triage4-fish:  steady / watch / urgent (matches)
#   - triage4-bird:  ok     / watch / urgent (adapter maps ok → steady)
#   - triage4-wild:  ok     / watch / urgent (adapter maps ok → steady)
# This is exactly the "Не слияние — совместимость"
# property: the portal does NOT push a renamed vocabulary
# back into the siblings.
VALID_LEVELS: tuple[str, ...] = ("urgent", "watch", "steady")


@dataclass(frozen=True)
class PortalEntry:
    """One sibling-emitted item, translated into a common shape.

    Adapters produce ``PortalEntry`` instances from native
    ``Report`` / ``Alert`` types. The portal NEVER mutates
    them.

    - ``sibling_id``: the package directory name, e.g.
      ``'triage4-fish'``. Must match a key in
      ``portal.coords.SIBLING_COORDS``.
    - ``entry_id``: sibling-local unique id (e.g. for an
      alert: ``f'{pen_id}:{kind}'``; for a score:
      ``score.pen_id``).
    - ``kind``: the alert kind or score channel
      (e.g. ``'gill_rate'``, ``'mortality_floor'``,
      ``'overall'``).
    - ``level``: ``'urgent'`` / ``'watch'`` / ``'steady'``.
    - ``location_handle``: opaque token, NEVER plaintext
      coordinates (every sibling enforces this on its own
      types via ``biocore.coords.DECIMAL_PAIR_RE``).
    - ``observed_value``: the per-channel safety value or
      raw observation when the sibling exposes one.
    - ``t_window``: optional ``(start_s, end_s)`` for time-
      based correlation. ``None`` if the sibling does not
      track windows.
    - ``payload``: free-form sibling-specific extras
      (species, watershed tag, station id, …). Kept as
      ``Mapping[str, object]`` so adapters don't have to
      conform to a fixed schema.
    """

    sibling_id: str
    entry_id: str
    kind: str
    level: str
    location_handle: str
    observed_value: float | None = None
    t_window: tuple[float, float] | None = None
    payload: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.sibling_id:
            raise ValueError("sibling_id must not be empty")
        if not self.entry_id:
            raise ValueError("entry_id must not be empty")
        if not self.kind:
            raise ValueError("kind must not be empty")
        if self.level not in VALID_LEVELS:
            raise ValueError(
                f"level must be one of {VALID_LEVELS}, "
                f"got {self.level!r}"
            )
        if not self.location_handle.strip():
            raise ValueError("location_handle must not be empty")
        if self.t_window is not None:
            start, end = self.t_window
            if start < 0 or end < start:
                raise ValueError(
                    f"t_window must be (start>=0, end>=start), "
                    f"got {self.t_window}"
                )

    @property
    def key(self) -> tuple[str, str]:
        """Portal-wide unique key."""
        return (self.sibling_id, self.entry_id)


@dataclass(frozen=True)
class Bridge:
    """One typed edge between two ``PortalEntry`` keys.

    ``evidence`` is the human-readable rationale the
    discovery rule emits — kept free-form so we can read
    it during demos / debugging without parsing a
    structured payload.
    """

    kind: BridgeKind
    from_key: tuple[str, str]
    to_key: tuple[str, str]
    evidence: str

    def __post_init__(self) -> None:
        if self.from_key == self.to_key:
            raise ValueError(
                f"Bridge endpoints must differ; got {self.from_key}"
            )
        if not self.evidence.strip():
            raise ValueError("Bridge evidence must not be empty")


__all__ = [
    "Bridge",
    "BridgeKind",
    "PortalEntry",
    "VALID_LEVELS",
]
