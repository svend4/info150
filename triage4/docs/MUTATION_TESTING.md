# triage4 — Mutation testing

Mutation testing complements ordinary unit tests by answering a
different question. Unit tests answer *"does my code do what I
expect?"*. Mutation tests answer *"if my code stopped doing what I
expect, would any test catch it?"*. Closes RISK_REGISTER **CI-002**.

`mutmut` introduces small, well-defined changes (mutants) to the
source — flip `<=` to `<`, replace `True` with `False`, remove a
return, etc. — and runs the full test suite against each mutant.
A mutant that passes the test suite ("survives") signals either a
weak test or dead code.

## Scope

Mutation testing is slow (full test suite × N mutants per module).
triage4 targets the *triage-critical* surface — modules where a
silent regression would be most dangerous:

| Module | Why it's in scope |
|---|---|
| `triage_reasoning/score_fusion.py` | Mortal-sign override logic (SAFE-001) |
| `triage_reasoning/rapid_triage.py` | Main triage decision |
| `triage_reasoning/larrey_baseline.py` | Regression baseline against modern engine |
| `triage_reasoning/celegans_net.py` | Independent second-opinion classifier |
| `mission_coordination/mission_triage.py` | Fractal mission-level escalation |
| `integrations/marker_codec.py` | Offline-handoff integrity (DATA-001) |
| `integrations/bridge_health.py` | Pre-dispatch safety gate |

The scope is declared in `pyproject.toml` under `[tool.mutmut]`.

Everything outside that set (matching, signatures, UI, examples,
adapters) is excluded for speed. Broader coverage is welcome once
the critical set is clean.

## Running

```bash
pip install -e '.[dev,mutation]'
./scripts/run_mutation.sh
```

Full run: ~5–15 min on a laptop. Quick partial:

```bash
./scripts/run_mutation.sh --quick        # score_fusion only
```

After a run, inspect survivors:

```bash
./scripts/run_mutation.sh results
./scripts/run_mutation.sh show 42        # diff for mutant 42
```

## Interpreting results

`mutmut results` buckets mutants:

- **killed** — a test failed on the mutant. Good.
- **survived** — no test noticed the change. Bad: either add a
  test or delete the code the mutant exercised.
- **timeout** — the mutant made the test suite loop forever. Treat
  as a killed mutant *unless* it indicates a real infinite-loop
  bug on the original.
- **skipped** — usually a no-op mutant on a comment or literal; ok.

### Acceptable survival rate

For the triage-critical scope above, aim for **survival ≤ 5%**.
That target is stricter than the common ~15% because these modules
are life-safety-adjacent.

Survivors should be triaged individually:

1. **Real gap** → add a test that would have killed it, commit.
2. **Equivalent mutant** (mutation changes the AST but not the
   semantics — e.g. reordering a commutative sum) → mark it off
   with an inline comment and move on.
3. **Dead code** → delete it.

## Not in CI (for now)

Mutation runs are not gated on every PR. Reasons:

- A full run is too slow for the per-PR latency budget.
- Baseline is established via an opt-in nightly workflow (future).
- Survivors should be reviewed by a human, not auto-rejected.

When the project gets a nightly CI budget, a scheduled workflow
can run `mutmut run` and surface survivors as issues.

## Known limitations

- `mutmut` does not mutate across modules; inter-module invariants
  need their own tests (e.g. `tests/test_end_to_end.py`).
- Numeric mutations on floating-point thresholds can produce
  equivalent mutants that pass trivially; tune thresholds via
  calibration (`triage_reasoning/calibration.py`) rather than
  manual bump-and-check.
- Property-based tests (hypothesis) complement mutation testing
  well; that work is tracked as a Level B item in the roadmap.

## References

- `pyproject.toml` — `[tool.mutmut]` scope declaration.
- `scripts/run_mutation.sh` — run / quick / results / show helper.
- `docs/RISK_REGISTER.md` — CI-002.
