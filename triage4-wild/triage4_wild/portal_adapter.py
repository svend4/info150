"""Optional portal adapter — translates ``ReserveReport`` outputs
into ``PortalEntry`` instances for cross-sibling coordination.

This module is the *only* coupling point between
``triage4-wild`` and ``portal``. The sibling stays
independently installable: nothing in this file is
imported from any other ``triage4-wild`` module, and
nothing in ``triage4-wild`` imports from here.

See ``docs/DOMAIN_ADAPTATIONS.md §8``.
"""

from __future__ import annotations

from collections.abc import Iterable

from portal.protocol import PortalEntry

from .core.models import ReserveReport


_SIBLING_ID = "triage4-wild"


# Wild's native AlertLevel uses ``ok`` for the calm tier; the
# portal canonicalises it as ``steady`` (the vocabulary fish
# already uses). Translation happens at the adapter boundary;
# the native sibling keeps its own labels.
_LEVEL_MAP: dict[str, str] = {
    "ok": "steady",
    "watch": "watch",
    "urgent": "urgent",
}


def adapt(report: ReserveReport) -> Iterable[PortalEntry]:
    """Yield ``PortalEntry`` instances for one ``ReserveReport``."""
    reserve = report.reserve_id

    for score in report.scores:
        yield PortalEntry(
            sibling_id=_SIBLING_ID,
            entry_id=f"{score.obs_token}:overall",
            kind="overall",
            level=_LEVEL_MAP[score.alert_level],
            location_handle=f"reserve-{reserve}-obs-{score.obs_token}",
            observed_value=score.overall,
            payload={
                "reserve_id": reserve,
                "gait_safety": score.gait_safety,
                "thermal_safety": score.thermal_safety,
                "postural_safety": score.postural_safety,
                "body_condition_safety": score.body_condition_safety,
                "threat_signal": score.threat_signal,
            },
        )

    for alert in report.alerts:
        yield PortalEntry(
            sibling_id=_SIBLING_ID,
            entry_id=f"{alert.obs_token}:{alert.kind}",
            kind=alert.kind,
            level=_LEVEL_MAP[alert.level],
            location_handle=alert.location_handle,
            observed_value=alert.observed_value,
            payload={"reserve_id": reserve, "obs_token": alert.obs_token},
        )


__all__ = ["adapt"]
