"""triage4 — scaling / memory stress benchmark.

Addresses Level C. The reference benchmark
(``full_pipeline_benchmark.py``) uses 8 casualties — enough to show
the pipeline works, not enough to reveal superlinear cost. This
script generates synthetic scenes of configurable size, runs the
triage-hot path (signatures → fusion → graph), and reports wall-
clock time + RSS memory per scale.

Output helps surface two things:

- **Scaling curve.** If the runtime grows significantly faster
  than N, a module has an O(N²) hiding somewhere. Current hot path
  is linear (by design), so doubling N ~doubles time.
- **Per-casualty memory.** If one casualty eats > ~5 KB of steady
  state, we are retaining something heavy (likely raw video stack
  or duplicate signature dicts).

Run from the project root:

    python examples/stress_benchmark.py                 # default: 10 / 100 / 500
    python examples/stress_benchmark.py --sizes 100 1000 5000
    python examples/stress_benchmark.py --json stress.json
"""

from __future__ import annotations

import argparse
import gc
import json
import resource
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4.core.models import CasualtyNode, CasualtySignature, GeoPose  # noqa: E402
from triage4.graph.casualty_graph import CasualtyGraph  # noqa: E402
from triage4.triage_reasoning.rapid_triage import RapidTriageEngine  # noqa: E402


_DEFAULT_SIZES = (10, 100, 500)


@dataclass
class ScaleResult:
    n: int
    elapsed_s: float
    rss_kb: int
    per_casualty_us: float
    per_casualty_kb: float
    immediate_fraction: float


def _rss_kb() -> int:
    """Resident-set size in KB (Linux; macOS reports bytes — we normalise)."""
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux: KB already. macOS: bytes. Heuristic: anything over 1 TB in KB
    # is almost certainly bytes.
    return int(usage / 1024) if usage > 2**40 else int(usage)


def _synthetic_signature(seed: int) -> CasualtySignature:
    rng = np.random.default_rng(seed)
    bleeding = float(rng.uniform(0.0, 1.0))
    chest_fd = float(rng.uniform(0.0, 1.0))
    return CasualtySignature(
        breathing_curve=[float(v) for v in rng.normal(0.0, 0.2, size=24)],
        chest_motion_fd=chest_fd,
        perfusion_drop_score=float(rng.uniform(0.0, 1.0)),
        thermal_asymmetry_score=float(rng.uniform(0.0, 1.0)),
        bleeding_visual_score=bleeding,
        posture_instability_score=float(rng.uniform(0.0, 1.0)),
        visibility_score=float(rng.uniform(0.5, 1.0)),
    )


def _generate_scene(n: int) -> list[tuple[str, CasualtySignature, GeoPose]]:
    return [
        (
            f"C{i:05d}",
            _synthetic_signature(seed=i),
            GeoPose(
                x=float((i * 13) % 400),
                y=float((i * 31) % 400),
            ),
        )
        for i in range(n)
    ]


def run_scale(n: int) -> ScaleResult:
    """Run the triage hot path on a synthetic scene of ``n`` casualties."""
    engine = RapidTriageEngine()
    graph = CasualtyGraph()

    scene = _generate_scene(n)

    gc.collect()
    rss_before = _rss_kb()
    t0 = time.perf_counter()

    immediate_count = 0
    for cid, sig, pose in scene:
        priority, _score, _reasons = engine.infer_priority(sig)
        node = CasualtyNode(
            id=cid,
            location=pose,
            platform_source="stress",
            confidence=0.8,
            status="assessed",
            signatures=sig,
            triage_priority=priority,
        )
        graph.upsert(node)
        if priority == "immediate":
            immediate_count += 1

    elapsed = time.perf_counter() - t0
    rss_after = _rss_kb()
    rss_delta = max(0, rss_after - rss_before)

    return ScaleResult(
        n=n,
        elapsed_s=round(elapsed, 4),
        rss_kb=rss_delta,
        per_casualty_us=round(elapsed * 1e6 / max(1, n), 2),
        per_casualty_kb=round(rss_delta / max(1, n), 3),
        immediate_fraction=round(immediate_count / max(1, n), 3),
    )


def _print_table(results: list[ScaleResult]) -> None:
    print("triage4 stress benchmark")
    print("=" * 70)
    print(f"{'N':>8} {'time (s)':>10} {'per-C (µs)':>12} {'ΔRSS (KB)':>11} {'per-C (KB)':>12} {'%imm':>6}")
    print("-" * 70)
    for r in results:
        print(
            f"{r.n:>8} {r.elapsed_s:>10.4f} {r.per_casualty_us:>12.2f} "
            f"{r.rss_kb:>11d} {r.per_casualty_kb:>12.3f} {r.immediate_fraction * 100:>5.1f}%"
        )
    print()
    if len(results) >= 2:
        a, b = results[0], results[-1]
        ratio_n = b.n / max(1, a.n)
        ratio_t = b.elapsed_s / max(1e-9, a.elapsed_s)
        slope = ratio_t / ratio_n if ratio_n else 0.0
        slope_label = (
            "~linear" if 0.7 <= slope <= 1.3
            else "super-linear (possible O(N²) hotspot)" if slope > 1.3
            else "sub-linear (batching / caching in effect)"
        )
        print(f"scale slope: time ratio / N ratio = {slope:.2f} — {slope_label}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--sizes", nargs="+", type=int, default=list(_DEFAULT_SIZES),
        help="casualty counts to benchmark (default: 10 100 500)",
    )
    parser.add_argument(
        "--json", metavar="PATH",
        help="write results as JSON to PATH",
    )
    args = parser.parse_args(argv)

    results = [run_scale(n) for n in args.sizes]
    _print_table(results)

    if args.json:
        Path(args.json).write_text(
            json.dumps([r.__dict__ for r in results], indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
