"""String-literal enums for the fitness domain.

No `enum.Enum` — triage4 established the pattern of
`Literal[...]` + plain strings for lightweight serialisation
and test ergonomics, and triage4-fit follows it.
"""

from __future__ import annotations

from typing import Literal


ExerciseKind = Literal["squat", "pushup", "deadlift"]

# Coaching-cue severity — NOT a triage priority. "ok" means the
# rep is fine; "minor" means "notice but don't stop"; "severe"
# means "the rep was compromised enough to suggest a rest set".
CueSeverity = Literal["ok", "minor", "severe"]

# Cue category — what the cue is about. Corresponds to the
# signature channels the engine monitors.
CueKind = Literal["asymmetry", "depth", "tempo", "breathing"]

VALID_EXERCISES: tuple[ExerciseKind, ...] = ("squat", "pushup", "deadlift")
VALID_SEVERITIES: tuple[CueSeverity, ...] = ("ok", "minor", "severe")
VALID_CUE_KINDS: tuple[CueKind, ...] = ("asymmetry", "depth", "tempo", "breathing")
