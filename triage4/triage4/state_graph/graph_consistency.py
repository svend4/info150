"""Triage-facing consistency checks built on top of the upstream primitives.

Reuses :class:`ConsistencyIssue` / :class:`ConsistencyReport` from
:mod:`triage4.scoring.consistency_checker` to validate a CasualtyGraph +
MissionGraph pair. This is where the document-specific checks (canvas
bounds, missing fragments) are dropped and triage-oriented ones
(orphan edges, low confidence, double handoff) are added.
"""

from __future__ import annotations

from triage4.graph.casualty_graph import CasualtyGraph
from triage4.graph.mission_graph import MissionGraph
from triage4.scoring.consistency_checker import (
    ConsistencyIssue,
    ConsistencyReport,
)


def _orphan_edge_issues(graph: CasualtyGraph) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []
    node_ids = set(graph.nodes)
    for src, rel, dst in graph.edges:
        missing: list[str] = []
        if src not in node_ids and not str(src).startswith(("uav", "ugv", "medic", "demo", "sim")):
            missing.append(str(src))
        if dst not in node_ids and not str(dst).startswith(("uav", "ugv", "medic", "demo", "sim", "map")):
            missing.append(str(dst))
        if missing:
            issues.append(
                ConsistencyIssue(
                    code="ORPHAN_EDGE",
                    description=(
                        f"edge ({src}, {rel}, {dst}) references unknown node(s): "
                        f"{missing}"
                    ),
                    severity="warning",
                )
            )
    return issues


def _low_confidence_issues(
    graph: CasualtyGraph, min_confidence: float
) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []
    for node in graph.all_nodes():
        if node.confidence < min_confidence:
            issues.append(
                ConsistencyIssue(
                    code="LOW_CONFIDENCE",
                    description=(
                        f"casualty {node.id} confidence "
                        f"{node.confidence:.2f} < {min_confidence}"
                    ),
                    severity="warning",
                )
            )
    return issues


def _immediate_without_handoff(
    graph: CasualtyGraph, mission: MissionGraph
) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []
    assigned = set(mission.medic_assignments.values())
    for node in graph.all_nodes():
        if node.triage_priority == "immediate" and node.id not in assigned:
            issues.append(
                ConsistencyIssue(
                    code="IMMEDIATE_WITHOUT_HANDOFF",
                    description=(
                        f"immediate casualty {node.id} has no medic assigned"
                    ),
                    severity="error",
                )
            )
    return issues


def _double_medic_assignment(mission: MissionGraph) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []
    seen: dict[str, str] = {}
    for medic, casualty in mission.medic_assignments.items():
        if casualty in seen:
            issues.append(
                ConsistencyIssue(
                    code="DOUBLE_HANDOFF",
                    description=(
                        f"casualty {casualty} is assigned to both medics "
                        f"{seen[casualty]} and {medic}"
                    ),
                    severity="error",
                )
            )
        seen[casualty] = medic
    return issues


def check_casualty_graph_consistency(
    graph: CasualtyGraph,
    mission: MissionGraph | None = None,
    min_confidence: float = 0.4,
) -> ConsistencyReport:
    """Run triage-specific consistency checks on a CasualtyGraph.

    Checks performed:
    - orphan edges (edge references an unknown casualty id)
    - low-confidence casualties (< ``min_confidence``)
    - immediate casualties without any medic assignment
    - a single casualty assigned to multiple medics
    """
    issues: list[ConsistencyIssue] = []
    issues.extend(_orphan_edge_issues(graph))
    issues.extend(_low_confidence_issues(graph, min_confidence))

    if mission is not None:
        issues.extend(_immediate_without_handoff(graph, mission))
        issues.extend(_double_medic_assignment(mission))

    n_errors = sum(1 for i in issues if i.severity == "error")
    n_warnings = sum(1 for i in issues if i.severity == "warning")

    return ConsistencyReport(
        issues=issues,
        is_consistent=(n_errors == 0),
        n_errors=n_errors,
        n_warnings=n_warnings,
        checked_pairs=len(graph.edges),
    )
