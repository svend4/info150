"""triage4 — Bayesian patient twin demo.

Shows how ``PatientTwinFilter`` turns repeated observations of one
casualty into a posterior distribution over priority bands, not just
a point estimate. Useful for operator UI (probability bar instead of
single label) and for downstream escalation logic (handoff if
P(immediate) > 0.8).

Run from the project root:

    python examples/bayesian_twin_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4.core.models import CasualtySignature  # noqa: E402
from triage4.triage_reasoning import PatientTwinFilter  # noqa: E402


def _critical() -> CasualtySignature:
    return CasualtySignature(
        breathing_curve=[0.01] * 6,
        chest_motion_fd=0.06,
        perfusion_drop_score=0.85,
        bleeding_visual_score=0.9,
        posture_instability_score=0.75,
    )


def _minimal() -> CasualtySignature:
    return CasualtySignature(
        breathing_curve=[0.25] * 6,
        chest_motion_fd=0.35,
        perfusion_drop_score=0.10,
        bleeding_visual_score=0.05,
        posture_instability_score=0.05,
    )


def _bar(prob: float, width: int = 20) -> str:
    full = int(round(prob * width))
    return "█" * full + "░" * (width - full)


def _show(label: str, twin: PatientTwinFilter, sig: CasualtySignature, ticks: int):
    print(f"\n== {label} ==")
    print("tick  P(imm)  P(del)  P(min)  ESS")
    for t in range(1, ticks + 1):
        post = twin.update(sig)
        p = post.priority_probs
        print(
            f"{t:>3d}   {p['immediate']:.2f}    {p['delayed']:.2f}    "
            f"{p['minimal']:.2f}    {post.effective_sample_size:.1f}"
        )
    final = twin.posterior()
    print(f"final: most likely = {final.most_likely_priority} "
          f"({final.most_likely_probability:.2f})")
    for band, p in final.priority_probs.items():
        print(f"  {band:<10s} |{_bar(p)}|  {p:.2f}")


def main() -> None:
    print("Bayesian patient twin — posterior convergence on two casualties")
    _show(
        "Casualty A — all mortal signs present",
        PatientTwinFilter(n_particles=200, seed=1),
        _critical(),
        ticks=6,
    )
    _show(
        "Casualty B — quiet / low severity",
        PatientTwinFilter(n_particles=200, seed=2),
        _minimal(),
        ticks=6,
    )


if __name__ == "__main__":
    main()
