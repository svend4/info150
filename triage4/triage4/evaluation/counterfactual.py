"""Retrospective counterfactual re-scoring of a mission.

Part of Phase 9c (innovation pack 2, idea #6). After a mission, given
actual triage decisions and eventual outcomes per casualty, estimate:

    for each casualty C and each hypothetical priority P,
    what would the expected survival / recovery outcome have been
    if we had assigned P instead of the priority we actually did?

Uses a simple monotonic outcome model — the probability of a good
outcome is higher when an ``immediate`` casualty was treated
immediately, and falls with response time. Not a substitute for clinical
epidemiology; a harness to quantify *our decisions* against a
defensible baseline model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


# Base survival probability given (true_severity, assigned_priority)
# under the assumption that the assigned priority drives response speed.
# Entries: P(good outcome | severity ∈ {critical, serious, light}, priority).
_OUTCOME_PRIORS: dict[tuple[str, str], float] = {
    ("critical", "immediate"): 0.85,
    ("critical", "delayed"): 0.40,
    ("critical", "minimal"): 0.10,
    ("serious", "immediate"): 0.95,
    ("serious", "delayed"): 0.85,
    ("serious", "minimal"): 0.60,
    ("light", "immediate"): 0.98,
    ("light", "delayed"): 0.97,
    ("light", "minimal"): 0.95,
}


@dataclass
class CounterfactualCase:
    casualty_id: str
    true_severity: str           # "critical" / "serious" / "light"
    actual_priority: str         # what the system assigned
    actual_outcome: float        # 0..1 recovered-or-survived
    counterfactuals: dict[str, float]   # priority → expected outcome
    best_alternative: str
    regret: float                # (best_alternative_outcome - actual_outcome)


@dataclass
class CounterfactualReport:
    cases: list[CounterfactualCase]
    mean_regret: float
    n_cases_with_regret: int
    n_total: int


def _expected_outcome(severity: str, priority: str) -> float:
    if severity not in {"critical", "serious", "light"}:
        raise ValueError(f"unknown severity '{severity}'")
    if priority not in {"immediate", "delayed", "minimal"}:
        raise ValueError(f"unknown priority '{priority}'")
    return _OUTCOME_PRIORS.get((severity, priority), 0.0)


def score_counterfactuals(
    casualty_id: str,
    true_severity: str,
    actual_priority: str,
    actual_outcome: float,
) -> CounterfactualCase:
    """Compute what-if outcomes for all alternative priorities."""
    if true_severity not in {"critical", "serious", "light"}:
        raise ValueError(f"unknown severity '{true_severity}'")
    if actual_priority not in {"immediate", "delayed", "minimal"}:
        raise ValueError(f"unknown priority '{actual_priority}'")
    if not 0.0 <= actual_outcome <= 1.0:
        raise ValueError(
            f"actual_outcome must be in [0, 1], got {actual_outcome}"
        )

    alternatives = {
        p: _expected_outcome(true_severity, p)
        for p in ("immediate", "delayed", "minimal")
    }
    best_priority = max(alternatives, key=lambda p: alternatives[p])
    best_outcome = alternatives[best_priority]
    regret = max(0.0, best_outcome - actual_outcome)

    return CounterfactualCase(
        casualty_id=casualty_id,
        true_severity=true_severity,
        actual_priority=actual_priority,
        actual_outcome=round(actual_outcome, 3),
        counterfactuals={k: round(v, 3) for k, v in alternatives.items()},
        best_alternative=best_priority,
        regret=round(regret, 3),
    )


def evaluate_counterfactuals(
    records: Sequence[tuple[str, str, str, float]],
    regret_threshold: float = 0.10,
) -> CounterfactualReport:
    """Score a sequence of ``(casualty_id, severity, priority, outcome)``."""
    if regret_threshold < 0.0:
        raise ValueError(f"regret_threshold must be >= 0, got {regret_threshold}")

    cases = [score_counterfactuals(*r) for r in records]
    n = len(cases)
    if n == 0:
        return CounterfactualReport(
            cases=[], mean_regret=0.0, n_cases_with_regret=0, n_total=0
        )

    mean_regret = sum(c.regret for c in cases) / n
    n_with_regret = sum(1 for c in cases if c.regret > regret_threshold)
    return CounterfactualReport(
        cases=cases,
        mean_regret=round(mean_regret, 3),
        n_cases_with_regret=n_with_regret,
        n_total=n,
    )
