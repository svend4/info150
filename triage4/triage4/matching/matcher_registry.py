"""Name-based registry of matcher / scorer functions.

Adapted from svend4/meta2 — ``puzzle_reconstruction/matching/matcher_registry.py``.
Original copyright (c) svend4, MIT-licensed (see ``LICENSES/meta2.LICENSE``).

Adaptation notes:
- Upstream signature was ``(EdgeSignature, EdgeSignature) -> float``.
- In triage4 the same pattern lets us register signature extractors or
  pair-wise matchers (``(CasualtySignature, CasualtySignature) -> float``)
  under stable names and compose them via ``compute_scores``.
"""

from __future__ import annotations

from typing import Any, Callable


MatcherFn = Callable[..., float]

MATCHER_REGISTRY: dict[str, MatcherFn] = {}


def register(name: str) -> Callable[[MatcherFn], MatcherFn]:
    """Декоратор для регистрации функции-скоринга под именем ``name``."""

    def _inner(fn: MatcherFn) -> MatcherFn:
        register_fn(name, fn)
        return fn

    return _inner


def register_fn(name: str, fn: MatcherFn) -> None:
    if not name:
        raise ValueError("matcher name must be non-empty")
    MATCHER_REGISTRY[name] = fn


def get_matcher(name: str) -> MatcherFn:
    if name not in MATCHER_REGISTRY:
        raise KeyError(f"matcher '{name}' is not registered")
    return MATCHER_REGISTRY[name]


def list_matchers() -> list[str]:
    return sorted(MATCHER_REGISTRY.keys())


def compute_scores(
    a: Any,
    b: Any | None = None,
    matchers: list[str] | None = None,
) -> dict[str, float]:
    """Run named matchers and return ``{name: score}``.

    If ``matchers`` is None, all registered matchers are run. ``b`` is
    optional so we can use the registry both for per-entity signature
    extraction (unary) and for pairwise matching (binary).
    """
    names = matchers if matchers is not None else list_matchers()
    out: dict[str, float] = {}
    for name in names:
        fn = get_matcher(name)
        try:
            out[name] = float(fn(a) if b is None else fn(a, b))
        except Exception:
            out[name] = 0.0
    return out
