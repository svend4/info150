"""Consistency reporting for an assembled state.

Adapted from svend4/meta2 — ``puzzle_reconstruction/scoring/consistency_checker.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Upstream validates a torn-document reassembly: unique IDs, no missing
fragments, all fragments inside the canvas, pair-wise scores above a
threshold, uniform gaps. triage4 reuses the same ``ConsistencyIssue`` /
``ConsistencyReport`` machinery to validate casualty graphs and mission
state; see :mod:`triage4.state_graph.graph_consistency` for a triage-facing
wrapper over these primitives.

Adaptation notes:
- Copied verbatim; error strings translated to English.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np


@dataclass
class ConsistencyIssue:
    """A single consistency issue."""

    code: str
    description: str
    fragment_ids: List[int] = field(default_factory=list)
    severity: str = "error"

    def __post_init__(self) -> None:
        valid = {"error", "warning", "info"}
        if self.severity not in valid:
            raise ValueError(
                f"severity must be one of {sorted(valid)}, got {self.severity!r}"
            )
        if not self.code:
            raise ValueError("code must not be empty")


@dataclass
class ConsistencyReport:
    """Full consistency report for an assembly."""

    issues: List[ConsistencyIssue]
    is_consistent: bool
    n_errors: int
    n_warnings: int
    checked_pairs: int = 0

    def __post_init__(self) -> None:
        if self.n_errors < 0:
            raise ValueError(f"n_errors must be >= 0, got {self.n_errors}")
        if self.n_warnings < 0:
            raise ValueError(f"n_warnings must be >= 0, got {self.n_warnings}")
        if self.checked_pairs < 0:
            raise ValueError(
                f"checked_pairs must be >= 0, got {self.checked_pairs}"
            )

    def __len__(self) -> int:
        return len(self.issues)


def check_unique_ids(fragment_ids: List[int]) -> List[ConsistencyIssue]:
    seen: Set[int] = set()
    duplicates: Set[int] = set()
    for fid in fragment_ids:
        if fid in seen:
            duplicates.add(fid)
        seen.add(fid)
    if duplicates:
        return [
            ConsistencyIssue(
                code="DUPLICATE_ID",
                description=f"duplicate ids: {sorted(duplicates)}",
                fragment_ids=sorted(duplicates),
                severity="error",
            )
        ]
    return []


def check_all_present(
    fragment_ids: List[int], expected_ids: List[int]
) -> List[ConsistencyIssue]:
    present = set(fragment_ids)
    expected = set(expected_ids)
    issues: List[ConsistencyIssue] = []

    missing = sorted(expected - present)
    if missing:
        issues.append(
            ConsistencyIssue(
                code="MISSING_FRAGMENT",
                description=f"missing fragments: {missing}",
                fragment_ids=missing,
                severity="error",
            )
        )

    extra = sorted(present - expected)
    if extra:
        issues.append(
            ConsistencyIssue(
                code="EXTRA_FRAGMENT",
                description=f"extra fragments: {extra}",
                fragment_ids=extra,
                severity="warning",
            )
        )
    return issues


def check_canvas_bounds(
    positions: List[Tuple[int, int]],
    sizes: List[Tuple[int, int]],
    canvas_w: int,
    canvas_h: int,
) -> List[ConsistencyIssue]:
    if canvas_w < 1:
        raise ValueError(f"canvas_w must be >= 1, got {canvas_w}")
    if canvas_h < 1:
        raise ValueError(f"canvas_h must be >= 1, got {canvas_h}")
    if len(positions) != len(sizes):
        raise ValueError(
            f"positions and sizes differ in length: "
            f"{len(positions)} != {len(sizes)}"
        )

    issues: List[ConsistencyIssue] = []
    for i, ((x, y), (w, h)) in enumerate(zip(positions, sizes)):
        if x < 0 or y < 0 or x + w > canvas_w or y + h > canvas_h:
            issues.append(
                ConsistencyIssue(
                    code="OUT_OF_BOUNDS",
                    description=(
                        f"fragment {i} outside canvas: "
                        f"({x},{y})+({w},{h}) > ({canvas_w},{canvas_h})"
                    ),
                    fragment_ids=[i],
                    severity="error",
                )
            )
    return issues


def check_score_threshold(
    pair_scores: Dict[Tuple[int, int], float], min_score: float = 0.5
) -> List[ConsistencyIssue]:
    if min_score < 0.0:
        raise ValueError(f"min_score must be >= 0, got {min_score}")

    issues: List[ConsistencyIssue] = []
    for (i, j), score in sorted(pair_scores.items()):
        if score < min_score:
            issues.append(
                ConsistencyIssue(
                    code="LOW_SCORE",
                    description=(
                        f"low pair score ({i},{j}): {score:.4f} < {min_score}"
                    ),
                    fragment_ids=[i, j],
                    severity="warning",
                )
            )
    return issues


def check_gap_uniformity(
    gaps: List[float], max_std: float = 5.0
) -> List[ConsistencyIssue]:
    if max_std < 0.0:
        raise ValueError(f"max_std must be >= 0, got {max_std}")
    if len(gaps) < 2:
        return []

    std = float(np.std(gaps, ddof=0))
    if std > max_std:
        return [
            ConsistencyIssue(
                code="NONUNIFORM_GAP",
                description=(
                    f"non-uniform gaps: std={std:.2f} > max_std={max_std}"
                ),
                severity="warning",
            )
        ]
    return []


def run_consistency_check(
    fragment_ids: List[int],
    expected_ids: List[int],
    positions: List[Tuple[int, int]],
    sizes: List[Tuple[int, int]],
    canvas_w: int,
    canvas_h: int,
    pair_scores: Optional[Dict[Tuple[int, int], float]] = None,
    min_score: float = 0.5,
) -> ConsistencyReport:
    all_issues: List[ConsistencyIssue] = []

    all_issues.extend(check_unique_ids(fragment_ids))
    all_issues.extend(check_all_present(fragment_ids, expected_ids))
    all_issues.extend(
        check_canvas_bounds(positions, sizes, canvas_w, canvas_h)
    )
    if pair_scores:
        all_issues.extend(check_score_threshold(pair_scores, min_score=min_score))

    n_errors = sum(1 for iss in all_issues if iss.severity == "error")
    n_warnings = sum(1 for iss in all_issues if iss.severity == "warning")
    checked_pairs = len(pair_scores) if pair_scores else 0

    return ConsistencyReport(
        issues=all_issues,
        is_consistent=(n_errors == 0),
        n_errors=n_errors,
        n_warnings=n_warnings,
        checked_pairs=checked_pairs,
    )


def batch_consistency_check(
    assemblies: List[Dict],
) -> List[ConsistencyReport]:
    results = []
    for asm in assemblies:
        report = run_consistency_check(
            fragment_ids=asm["fragment_ids"],
            expected_ids=asm["expected_ids"],
            positions=asm["positions"],
            sizes=asm["sizes"],
            canvas_w=asm["canvas_w"],
            canvas_h=asm["canvas_h"],
            pair_scores=asm.get("pair_scores"),
            min_score=asm.get("min_score", 0.5),
        )
        results.append(report)
    return results
