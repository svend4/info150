"""Optional portal adapter — translates ``StationReport`` outputs
into ``PortalEntry`` instances for cross-sibling coordination.

This module is the *only* coupling point between
``triage4-bird`` and ``portal``. The sibling stays
independently installable: nothing in this file is
imported from any other ``triage4-bird`` module, and
nothing in ``triage4-bird`` imports from here.

See ``docs/DOMAIN_ADAPTATIONS.md §8``.
"""

from __future__ import annotations

from collections.abc import Iterable

from portal.protocol import PortalEntry

from .core.models import StationReport


_SIBLING_ID = "triage4-bird"


# Bird's native AlertLevel uses ``ok`` for the calm tier; the
# portal canonicalises it as ``steady`` (the vocabulary fish
# already uses). The translation lives in the adapter — the
# native sibling keeps its own labels.
_LEVEL_MAP: dict[str, str] = {
    "ok": "steady",
    "watch": "watch",
    "urgent": "urgent",
}


def adapt(report: StationReport) -> Iterable[PortalEntry]:
    """Yield ``PortalEntry`` instances for one ``StationReport``."""
    station = report.station_id

    for score in report.scores:
        yield PortalEntry(
            sibling_id=_SIBLING_ID,
            entry_id=f"{score.obs_token}:overall",
            kind="overall",
            level=_LEVEL_MAP[score.alert_level],
            location_handle=f"station-{station}-obs-{score.obs_token}",
            observed_value=score.overall,
            payload={
                "station_id": station,
                "call_presence_safety": score.call_presence_safety,
                "distress_safety": score.distress_safety,
                "vitals_safety": score.vitals_safety,
                "thermal_safety": score.thermal_safety,
                "mortality_cluster_safety": score.mortality_cluster_safety,
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
            payload={"station_id": station, "obs_token": alert.obs_token},
        )


__all__ = ["adapt"]
