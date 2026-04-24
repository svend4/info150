# triage4-farm

> Stand-off livestock welfare observation library — sibling of
> [`triage4`](../triage4/), framed as **herd-welfare monitoring**,
> explicitly **not veterinary treatment recommendations**.

The second civilian sibling produced from the DOMAIN_ADAPTATIONS
catalog (entry **10 livestock / agtech**). Reuses the decision-
support infrastructure of triage4 — signatures, uncertainty
propagation, grounded explanations — and adapts the output to the
farmer + herd-vet workflow.

**This is an MVP prototype.** Scope is deliberately narrow:

- Observe a herd of cows / pigs / chickens on barn cameras.
- Score each animal for lameness / respiratory distress /
  thermal inflammation.
- Flag animals needing vet review.
- Never prescribe treatment. Never recommend antibiotic dosing.
  Those are veterinary decisions that are illegal (and unsafe)
  for an automated system to make in most jurisdictions.

## Philosophy

See [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md). Short version:
this is an **observation tool**. The farmer or herd vet acts on
the observations. We don't diagnose, we don't treat, we don't
recommend withdrawal periods or dosing. The system's output
always ends in "vet review recommended" — never "administer X".

## Vocabulary

| triage4 | triage4-farm |
|---|---|
| CasualtyNode | AnimalObservation |
| triage_priority | welfare_flag |
| immediate / delayed / minimal | urgent / concern / well |
| RapidTriageEngine | WelfareCheckEngine |
| MedicHandoff | VetReferral / FarmerAlert |
| infer_priority | review |
| "patient" | "animal" / "head of livestock" |

No re-import of the `triage4` package. This is a copy-fork
(DOMAIN_ADAPTATIONS.md §7 anti-pattern — no premature `biocore/`
extraction).

## Quickstart

```bash
cd triage4-farm
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
make install-dev
make qa                             # ruff + mypy + pytest
make demo                           # one synthetic herd, printed alerts
```

## Status

See [`STATUS.md`](STATUS.md) for what's built and what's not.
In short: core dataclasses + 3 species profiles (dairy cow, pig,
chicken) + lameness / respiratory / thermal signatures + welfare
engine + synthetic herd generator + ~25 tests. No UI, no real-
camera integration, no ear-tag OCR.

## License

MIT. No third-party code vendored.
