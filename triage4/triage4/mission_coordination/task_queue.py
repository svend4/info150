from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict


@dataclass
class Task:
    casualty_id: str
    kind: str
    priority: str
    confidence: float

    def to_dict(self) -> dict:
        return asdict(self)


class TaskQueue:
    """FIFO queue of operator/robot tasks with simple dedup by casualty+kind."""

    def __init__(self) -> None:
        self._items: deque[Task] = deque()
        self._seen: set[tuple[str, str]] = set()

    def push(self, task: Task) -> None:
        key = (task.casualty_id, task.kind)
        if key in self._seen:
            return
        self._items.append(task)
        self._seen.add(key)

    def pop(self) -> Task | None:
        if not self._items:
            return None
        task = self._items.popleft()
        self._seen.discard((task.casualty_id, task.kind))
        return task

    def as_list(self) -> list[dict]:
        return [t.to_dict() for t in self._items]

    def __len__(self) -> int:
        return len(self._items)
