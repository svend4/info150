"""triage4 — minimal single-casualty example.

Shows the smallest useful pipeline: take a set of signatures, run rapid
triage, and print the priority + explanation + confidence.

Run from the project root:

    python examples/quick_triage.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4.core.models import CasualtySignature  # noqa: E402
from triage4.triage_reasoning import (  # noqa: E402
    RapidTriageEngine,
    UncertaintyModel,
)


def main() -> None:
    # A single simulated casualty: weak chest motion, strong bleeding,
    # poor perfusion. Represents a critically wounded person.
    sig = CasualtySignature(
        breathing_curve=[0.01, 0.02, 0.01, 0.02, 0.01, 0.02],
        chest_motion_fd=0.08,
        perfusion_drop_score=0.82,
        bleeding_visual_score=0.91,
        thermal_asymmetry_score=0.55,
        posture_instability_score=0.7,
        visibility_score=0.9,
        raw_features={
            "breathing_quality": 0.85,
            "perfusion_quality": 0.8,
            "bleeding_confidence": 0.9,
            "thermal_quality": 0.6,
        },
    )

    triage_engine = RapidTriageEngine()
    priority, score, reasons = triage_engine.infer_priority(sig)
    hypotheses = triage_engine.build_hypotheses(sig)

    uncertainty = UncertaintyModel().from_signature(sig, base_score=score)

    print(f"priority:             {priority}")
    print(f"raw score:            {score:.3f}")
    print(f"overall confidence:   {uncertainty.overall_confidence:.3f}")
    print(f"adjusted score:       {uncertainty.adjusted_score:.3f}")

    print("\nreasons:")
    for r in reasons:
        print(f"  - {r}")

    print("\nhypotheses:")
    for h in hypotheses:
        print(f"  - {h.kind:<22s} score={h.score:.2f}  {h.explanation}")

    # Explainability builder expects a CasualtyNode, so skip it here for
    # brevity; see full_pipeline_benchmark.py for the complete path.
    print("\nper-channel confidence:")
    for channel, conf in uncertainty.per_channel_confidence.items():
        print(f"  {channel:<24s} {conf:.2f}")


if __name__ == "__main__":
    main()
