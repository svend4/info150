from __future__ import annotations

from triage4.world_replay.timeline_store import TimelineStore


class ReplayEngine:
    """Steps through a TimelineStore deterministically for replay views."""

    def __init__(self, store: TimelineStore) -> None:
        self.store = store
        self._idx = 0

    def reset(self) -> None:
        self._idx = 0

    def next_frame(self) -> dict | None:
        frames = self.store.frames()
        if not frames:
            return None
        frame = frames[self._idx % len(frames)]
        self._idx += 1
        return frame

    def frame_at(self, index: int) -> dict | None:
        frames = self.store.frames()
        if not frames:
            return None
        return frames[index % len(frames)]
