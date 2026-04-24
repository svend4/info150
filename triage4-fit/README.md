# triage4-fit

> Stand-off fitness / wellness coaching cue engine — sibling of
> [`triage4`](../triage4/), deliberately framed as **wellness, not
> clinical**.

The first civilian sibling produced from the DOMAIN_ADAPTATIONS
catalog (entry **04 fitness / wellness**). Reuses the decision-
support infrastructure of triage4 — `FrameSource` pattern,
Eulerian vitals, posture symmetry, grounded explanations,
uncertainty propagation — and drops everything with a medical
framing.

**This is an MVP prototype.** Scope is deliberately narrow:

- Observe reps of a small set of exercises (squat / pushup /
  deadlift).
- Produce coaching cues ("left hip dropped on rep 3 — focus on
  symmetry").
- Track post-set recovery.
- Never diagnose, never treat, never recommend intensity changes
  that a certified trainer wouldn't.

## Philosophy

See [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md). The short version:
wellness products and clinical products **must not share a
process**. This package has no regulatory surface on purpose — it
supports the "gym / trainer" role, not the "medic / physician"
role.

## Vocabulary

| triage4 | triage4-fit |
|---|---|
| CasualtyNode | ExerciseSession |
| triage_priority | form_quality |
| immediate / delayed / minimal | severe_cue / minor_cue / ok |
| RapidTriageEngine | RapidFormEngine |
| MedicHandoff | CoachBriefing |
| infer_priority | review |
| "patient" | "trainee" |

No re-import of the `triage4` package. The sibling is a
copy-fork; shared abstractions migrate upstream to a `biocore/`
package only after ≥ 3 siblings converge on identical interfaces
(see DOMAIN_ADAPTATIONS.md §7).

## Quickstart

```bash
cd triage4-fit
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
make install-dev
make qa                             # ruff + mypy + pytest
make demo                           # one synthetic session, printed cues
```

## Status

See [`STATUS.md`](STATUS.md) for what's built and what's not.
In short: core dataclasses + 3 exercise profiles + symmetry-based
form engine + synthetic session generator + ~15 tests. No UI, no
real-camera integration — that belongs to a later iteration once
the API surface is stable.

## License

MIT. No third-party code vendored.
