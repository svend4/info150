from __future__ import annotations


class MissionGraph:
    """Tracks robot/medic assignments, unresolved sectors and revisit queue."""

    def __init__(self) -> None:
        self.robot_assignments: dict[str, str] = {}
        self.medic_assignments: dict[str, str] = {}
        self.unresolved_regions: set[str] = set()
        self.revisit_queue: list[str] = []

    def assign_robot(self, robot_id: str, casualty_id: str) -> None:
        self.robot_assignments[robot_id] = casualty_id

    def assign_medic(self, medic_id: str, casualty_id: str) -> None:
        self.medic_assignments[medic_id] = casualty_id

    def mark_unresolved(self, region_id: str) -> None:
        self.unresolved_regions.add(region_id)

    def resolve_region(self, region_id: str) -> None:
        self.unresolved_regions.discard(region_id)

    def enqueue_revisit(self, casualty_id: str) -> None:
        if casualty_id not in self.revisit_queue:
            self.revisit_queue.append(casualty_id)

    def as_json(self) -> dict:
        return {
            "robot_assignments": dict(self.robot_assignments),
            "medic_assignments": dict(self.medic_assignments),
            "unresolved_regions": sorted(self.unresolved_regions),
            "revisit_queue": list(self.revisit_queue),
        }
