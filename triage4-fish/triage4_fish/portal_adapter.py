"""Optional portal adapter — translates ``PenReport`` outputs
into ``PortalEntry`` instances for cross-sibling coordination.

This module is the *only* coupling point between
``triage4-fish`` and ``portal``. The sibling stays
independently installable: nothing in this file is
imported from any other ``triage4-fish`` module, and
nothing in ``triage4-fish`` imports from here.

Adapter contract: ``adapt(report)`` returns an iterable of
``PortalEntry`` items. One entry per alert (``kind`` set
to the alert's channel name) plus one ``overall`` entry
per per-pen score. The portal NEVER mutates the input
report.

See ``docs/DOMAIN_ADAPTATIONS.md §8`` for the policy this
implements ("Не слияние — совместимость").
"""

from __future__ import annotations

from collections.abc import Iterable

from portal.protocol import PortalEntry

from .core.models import PenReport


_SIBLING_ID = "triage4-fish"


def adapt(report: PenReport) -> Iterable[PortalEntry]:
    """Yield ``PortalEntry`` instances for one ``PenReport``."""
    farm = report.farm_id

    for score in report.scores:
        yield PortalEntry(
            sibling_id=_SIBLING_ID,
            entry_id=f"{score.pen_id}:overall",
            kind="overall",
            level=score.welfare_level,
            location_handle=f"farm-{farm}-pen-{score.pen_id}",
            observed_value=score.overall,
            payload={
                "farm_id": farm,
                "gill_rate_safety": score.gill_rate_safety,
                "school_cohesion_safety": score.school_cohesion_safety,
                "sea_lice_safety": score.sea_lice_safety,
                "mortality_safety": score.mortality_safety,
                "water_chemistry_safety": score.water_chemistry_safety,
            },
        )

    for alert in report.alerts:
        yield PortalEntry(
            sibling_id=_SIBLING_ID,
            entry_id=f"{alert.pen_id}:{alert.kind}",
            kind=alert.kind,
            level=alert.level,
            location_handle=alert.location_handle,
            observed_value=alert.observed_value,
            payload={"farm_id": farm, "pen_id": alert.pen_id},
        )


__all__ = ["adapt"]
