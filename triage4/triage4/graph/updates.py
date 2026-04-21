from __future__ import annotations

from triage4.core.models import CasualtyNode
from triage4.graph.casualty_graph import CasualtyGraph
from triage4.graph.mission_graph import MissionGraph


class GraphUpdateService:
    """Coordinates updates across casualty and mission graphs."""

    def __init__(self, casualty_graph: CasualtyGraph, mission_graph: MissionGraph) -> None:
        self.casualty_graph = casualty_graph
        self.mission_graph = mission_graph

    def ingest_assessment(self, casualty: CasualtyNode) -> None:
        self.casualty_graph.upsert(casualty)
        self.casualty_graph.link(casualty.id, "located_in", casualty.location.frame)
        if casualty.assigned_robot:
            self.casualty_graph.link(casualty.assigned_robot, "observed", casualty.id)
            self.mission_graph.assign_robot(casualty.assigned_robot, casualty.id)
        if casualty.assigned_medic:
            self.mission_graph.assign_medic(casualty.assigned_medic, casualty.id)
