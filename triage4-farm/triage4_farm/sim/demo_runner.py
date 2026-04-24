"""Small runnable demo — entry point for ``make demo``.

Keeps the Makefile clean and gives tests a single call site to
exercise the end-to-end pipeline deterministically.
"""

from __future__ import annotations

from ..welfare_check.welfare_engine import WelfareCheckEngine
from .synthetic_herd import demo_herd


def run_demo() -> str:
    herd = demo_herd(n_animals=6, n_lame=2)
    report = WelfareCheckEngine().review(
        farm_id="demo_farm",
        observations=herd,
    )
    return report.as_text()


if __name__ == "__main__":
    print(run_demo())
