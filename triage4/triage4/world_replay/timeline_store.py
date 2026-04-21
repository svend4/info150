from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TimelineFrame:
    t: float
    payload: dict = field(default_factory=dict)


class TimelineStore:
    """Append-only store of timestamped scene snapshots."""

    def __init__(self) -> None:
        self._frames: list[TimelineFrame] = []

    def record(self, t: float, payload: dict) -> None:
        self._frames.append(TimelineFrame(t=float(t), payload=dict(payload)))

    def frames(self) -> list[dict]:
        return [{"t": f.t, **f.payload} for f in self._frames]

    def __len__(self) -> int:
        return len(self._frames)
