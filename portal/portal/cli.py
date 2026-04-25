"""``portal demo`` — cross-sibling smoke command.

Imports the three pilot siblings (``triage4-fish``,
``triage4-bird``, ``triage4-wild``), runs each through its
own engine + synthetic generator, calls the per-sibling
adapter to produce ``PortalEntry`` items, runs
``discover_all`` and prints discovered bridges as a table.

Imports are lazy and per-sibling. A pilot sibling that is
not installed is skipped with a warning rather than
breaking the demo — supports the "optional participation"
property of the portal policy.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from typing import Callable

from .discovery import discover_all
from .protocol import PortalEntry
from .registry import BridgeRegistry


def _fish_entries() -> list[PortalEntry]:
    from triage4_fish.core.models import PenReport
    from triage4_fish.pen_health.monitoring_engine import (
        AquacultureHealthEngine,
    )
    from triage4_fish.portal_adapter import adapt
    from triage4_fish.sim.synthetic_pen import demo_observations

    engine = AquacultureHealthEngine()
    aggregate = PenReport(farm_id="DEMO_FARM")
    for obs in demo_observations():
        r = engine.review(obs, farm_id="DEMO_FARM")
        aggregate.scores.extend(r.scores)
        aggregate.alerts.extend(r.alerts)
    return list(adapt(aggregate))


def _bird_entries() -> list[PortalEntry]:
    from triage4_bird.bird_health.monitoring_engine import AvianHealthEngine
    from triage4_bird.core.models import StationReport
    from triage4_bird.portal_adapter import adapt
    from triage4_bird.sim.synthetic_station import demo_observations

    engine = AvianHealthEngine()
    # Aggregate per-observation reports into one StationReport so the
    # adapter sees the full demo at once. Use the first observation's
    # station_id since every demo obs runs against the same station.
    obs_list = demo_observations()
    station_id = obs_list[0].station_id if obs_list else "DEMO_STATION"
    aggregate = StationReport(station_id=station_id)
    for obs in obs_list:
        r = engine.review(obs)
        aggregate.scores.extend(r.scores)
        aggregate.alerts.extend(r.alerts)
    return list(adapt(aggregate))


def _wild_entries() -> list[PortalEntry]:
    from triage4_wild.core.models import ReserveReport
    from triage4_wild.portal_adapter import adapt
    from triage4_wild.sim.synthetic_reserve import demo_observations
    from triage4_wild.wildlife_health.monitoring_engine import (
        WildlifeHealthEngine,
    )

    engine = WildlifeHealthEngine()
    aggregate = ReserveReport(reserve_id="DEMO_RESERVE")
    for obs in demo_observations():
        r = engine.review(obs, reserve_id="DEMO_RESERVE")
        aggregate.scores.extend(r.scores)
        aggregate.alerts.extend(r.alerts)
    return list(adapt(aggregate))


_PILOT_SOURCES: tuple[tuple[str, Callable[[], list[PortalEntry]]], ...] = (
    ("triage4-fish", _fish_entries),
    ("triage4-bird", _bird_entries),
    ("triage4-wild", _wild_entries),
)


def cmd_demo() -> int:
    print("portal demo — cross-sibling coordination smoke")
    print("=" * 64)

    entries: list[PortalEntry] = []
    for sibling_id, source in _PILOT_SOURCES:
        try:
            new = source()
        except ImportError as e:
            print(f"[skip] {sibling_id} not installed: {e}")
            continue
        print(f"[ok]   {sibling_id}: {len(new)} portal entries")
        entries.extend(new)

    if not entries:
        print()
        print("No pilot siblings installed; nothing to discover.")
        return 0

    print()
    print(f"Total portal entries: {len(entries)}")
    by_sibling: dict[str, int] = {}
    for entry in entries:
        by_sibling[entry.sibling_id] = by_sibling.get(entry.sibling_id, 0) + 1
    for s, n in sorted(by_sibling.items()):
        print(f"  {s}: {n}")

    bridges = discover_all(entries)
    registry = BridgeRegistry()
    inserted = registry.extend(bridges)
    print()
    print(f"Discovered bridges: {inserted}")

    if not inserted:
        print("(no cross-sibling relationships in this batch — all pilot")
        print(" demos run independent fixtures, so this is expected when")
        print(" no synthetic alerts overlap.)")
        return 0

    print()
    print(f"{'kind':22s}  {'from':30s}  {'to':30s}  evidence")
    print("-" * 100)
    for b in registry:
        from_s = f"{b.from_key[0]}/{b.from_key[1]}"
        to_s = f"{b.to_key[0]}/{b.to_key[1]}"
        if len(from_s) > 30:
            from_s = from_s[:27] + "..."
        if len(to_s) > 30:
            to_s = to_s[:27] + "..."
        print(f"{b.kind.value:22s}  {from_s:30s}  {to_s:30s}  {b.evidence}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="portal",
        description=(
            "Read-only cross-sibling coordination layer. "
            "'Не слияние — совместимость' (not merger — compatibility)."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser(
        "demo",
        help="Run pilot siblings + discover cross-sibling bridges.",
    )

    args = parser.parse_args(argv)
    if args.cmd == "demo":
        return cmd_demo()
    return 2  # unreachable — argparse rejects unknown subcommands


if __name__ == "__main__":
    sys.exit(main())
