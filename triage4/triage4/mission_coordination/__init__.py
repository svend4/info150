"""K3-3.2 Mission Coordination Layer.

Assignment and task-queue primitives for coordinating robots and medics
against prioritized casualties.
"""

from .task_queue import TaskQueue
from .assignment_engine import AssignmentEngine
from .mission_triage import (
    DEFAULT_MISSION_WEIGHTS,
    MissionPriority,
    MissionSignature,
    MissionTriageResult,
    classify_mission,
    compute_mission_signature,
    triage_mission,
)

__all__ = [
    "AssignmentEngine",
    "DEFAULT_MISSION_WEIGHTS",
    "MissionPriority",
    "MissionSignature",
    "MissionTriageResult",
    "TaskQueue",
    "classify_mission",
    "compute_mission_signature",
    "triage_mission",
]
