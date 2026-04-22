"""Digital Baron Larrey — historical triage baseline.

Part of Phase 9a (innovation pack, idea #4). A deliberately simple
classifier that reproduces the decision principles of
**Dominique-Jean Larrey** (1766–1842), Napoleon's chief military
surgeon and the inventor of modern battlefield triage.

Larrey's original system (1797, codified 1812) had three categories:

1. *Dangereusement blessés* — dangerously wounded, whose life depends
   on immediate surgery.
2. *Moins dangereusement blessés* — less seriously wounded, whose
   treatment can be delayed without losing the patient.
3. *Légèrement blessés* — slightly wounded, who can walk and wait.

It worked on **visible signs available to a surgeon in a field tent
without instruments**: heavy bleeding, loss of consciousness, inability
to ambulate, major limb trauma.

Why a baseline:
- 200 years of battlefield validation (Napoleonic Wars, Waterloo, then
  every war since). An ML priority classifier that does *worse* than
  Larrey on synthetic benchmarks has no business being deployed.
- It is trivial to audit and explain, so any disagreement with the
  modern engine is a testable hypothesis, not a black-box mismatch.

Usage:
    baseline = LarreyBaselineTriage()
    priority = baseline.classify(sig)                    # quick
    priority, reasons = baseline.classify_with_reasons(sig)

Plug into the DARPA Gate 2 evaluator for a direct comparison against
``RapidTriageEngine``.
"""

from __future__ import annotations

from triage4.core.models import CasualtySignature


class LarreyBaselineTriage:
    """A 1797-style classifier, minus anything requiring 20th-century tech."""

    def __init__(
        self,
        heavy_bleeding: float = 0.7,
        absent_motion: float = 0.1,
        severe_posture: float = 0.7,
    ) -> None:
        if not 0.0 <= heavy_bleeding <= 1.0:
            raise ValueError("heavy_bleeding must be in [0, 1]")
        if not 0.0 <= absent_motion <= 1.0:
            raise ValueError("absent_motion must be in [0, 1]")
        if not 0.0 <= severe_posture <= 1.0:
            raise ValueError("severe_posture must be in [0, 1]")
        self.heavy_bleeding = heavy_bleeding
        self.absent_motion = absent_motion
        self.severe_posture = severe_posture

    def _mortal_signs(self, sig: CasualtySignature) -> list[str]:
        """Signs a Napoleonic surgeon would read as 'life-threatening'."""
        signs: list[str] = []
        if sig.bleeding_visual_score >= self.heavy_bleeding:
            signs.append("heavy visible bleeding")
        if (
            sig.chest_motion_fd < self.absent_motion
            and len(sig.breathing_curve) >= 4
        ):
            signs.append("no visible breathing")
        if sig.posture_instability_score >= self.severe_posture:
            signs.append("collapsed / unresponsive posture")
        return signs

    def _serious_signs(self, sig: CasualtySignature) -> list[str]:
        """Treatable with delay — a wound visible but subject still responsive."""
        signs: list[str] = []
        if 0.3 <= sig.bleeding_visual_score < self.heavy_bleeding:
            signs.append("moderate bleeding")
        if 0.3 <= sig.posture_instability_score < self.severe_posture:
            signs.append("unstable posture but still upright-ish")
        if sig.perfusion_drop_score > 0.4:
            signs.append("pallor / perfusion drop")
        return signs

    def classify(self, sig: CasualtySignature) -> str:
        """Return one of: 'immediate', 'delayed', 'minimal'."""
        if self._mortal_signs(sig):
            return "immediate"
        if self._serious_signs(sig):
            return "delayed"
        return "minimal"

    def classify_with_reasons(
        self, sig: CasualtySignature
    ) -> tuple[str, list[str]]:
        mortal = self._mortal_signs(sig)
        if mortal:
            return "immediate", mortal
        serious = self._serious_signs(sig)
        if serious:
            return "delayed", serious
        return "minimal", ["no visible distress"]
