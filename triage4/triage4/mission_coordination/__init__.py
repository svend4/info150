"""K3-3.2 Mission Coordination Layer.

Assignment and task-queue primitives for coordinating robots and medics
against prioritized casualties.
"""

from .task_queue import TaskQueue
from .assignment_engine import AssignmentEngine

__all__ = ["TaskQueue", "AssignmentEngine"]
