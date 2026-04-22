"""Fixed-topology, hand-wired triage classifier.

Part of Phase 9e (speculative). Inspired by the fact that *C. elegans*
makes all of its survival-relevant decisions with 302 fully-described
neurons and **no gradient-based training**. We don't need a roundworm's
full connectome; the point is methodological: an auditable,
hand-wired, small classifier can rival heuristic score fusion on
triage-like tasks while being trivial to inspect.

The network has three layers:
- **Sensory** (4 neurons) — bleeding, chest_motion_risk, perfusion,
  posture. Values read directly from ``CasualtySignature``.
- **Interneuron** (6 neurons) with biologically-inspired roles
  (hemorrhage_sense, respiratory_sense, shock_sense, pain_sense,
  mortal_aggregator, stability_sense).
- **Motor** (3 neurons) — one per priority band (immediate / delayed /
  minimal). Softmax over motor activations.

Weights are set from clinical priors, NOT trained. Every weight is
defensible from a single clinical observation:
- heavier bleeding excites hemorrhage_sense, which excites mortal;
- weak chest motion excites respiratory_sense, which excites mortal;
- stable posture inhibits mortal;
- mortal_aggregator strongly excites immediate motor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from triage4.core.models import CasualtySignature


_SENSORY = ("bleeding", "motion_risk", "perfusion", "posture")
_INTERNEURONS = (
    "hemorrhage_sense",
    "respiratory_sense",
    "shock_sense",
    "pain_sense",
    "mortal_aggregator",
    "stability_sense",
)
_MOTORS = ("immediate", "delayed", "minimal")


# Hand-authored weight matrices. Rows = destination, columns = source.
#                       bleed   motion   perf    post
_W_SENSORY_TO_INTER: dict[str, dict[str, float]] = {
    "hemorrhage_sense":   {"bleeding":  1.5, "motion_risk": 0.0, "perfusion":  0.6, "posture": 0.0},
    "respiratory_sense":  {"bleeding":  0.0, "motion_risk": 1.6, "perfusion":  0.2, "posture": 0.0},
    "shock_sense":        {"bleeding":  0.5, "motion_risk": 0.2, "perfusion":  1.4, "posture": 0.3},
    "pain_sense":         {"bleeding":  0.4, "motion_risk": 0.2, "perfusion":  0.2, "posture": 0.6},
    "mortal_aggregator":  {"bleeding":  1.0, "motion_risk": 1.0, "perfusion":  0.8, "posture": 0.6},
    "stability_sense":    {"bleeding": -0.9, "motion_risk":-0.9, "perfusion": -0.7, "posture":-0.9},
}


_W_INTER_TO_MOTOR: dict[str, dict[str, float]] = {
    "immediate": {
        "hemorrhage_sense": 1.3, "respiratory_sense": 1.3, "shock_sense": 1.1,
        "pain_sense": 0.4, "mortal_aggregator": 1.6, "stability_sense": -1.2,
    },
    "delayed": {
        "hemorrhage_sense": 0.5, "respiratory_sense": 0.5, "shock_sense": 0.8,
        "pain_sense": 1.0, "mortal_aggregator": 0.3, "stability_sense": -0.2,
    },
    "minimal": {
        "hemorrhage_sense": -0.7, "respiratory_sense": -0.7, "shock_sense": -0.6,
        "pain_sense": 0.2, "mortal_aggregator": -1.3, "stability_sense": 1.3,
    },
}


# Motor biases — the clinical default is "not immediate, not delayed,
# probably minimal". A casualty becomes immediate only when positive
# evidence overcomes the bias, echoing the Larrey 1797 rule that
# triage escalation requires a witnessed mortal sign.
_MOTOR_BIAS: dict[str, float] = {
    "immediate": -0.5,
    "delayed": -0.2,
    "minimal": 0.5,
}


# Motion-risk is derived from ``chest_motion_fd`` via a clinical
# threshold: strong motion (≥ 0.30) → risk 0, absent motion (≤ 0.05)
# → risk 1, linear between. This avoids the "1 − x" trap that leaks
# mortal signal for healthy casualties.
_MOTION_RISK_CEIL = 0.30
_MOTION_RISK_FLOOR = 0.05


@dataclass
class NetActivation:
    sensory: dict[str, float]
    interneuron: dict[str, float]
    motor: dict[str, float]
    priority: str


def _activate(value: float) -> float:
    """Saturating non-linearity — tanh, centred at 0, bounded in (-1, 1)."""
    return math.tanh(float(value))


def _sensory_from_signature(sig: CasualtySignature) -> dict[str, float]:
    if len(sig.breathing_curve) < 4:
        motion_risk = 0.0
    else:
        span = _MOTION_RISK_CEIL - _MOTION_RISK_FLOOR
        motion_risk = (_MOTION_RISK_CEIL - float(sig.chest_motion_fd)) / span
        motion_risk = max(0.0, min(1.0, motion_risk))
    return {
        "bleeding": max(0.0, min(1.0, sig.bleeding_visual_score)),
        "motion_risk": motion_risk,
        "perfusion": max(0.0, min(1.0, sig.perfusion_drop_score)),
        "posture": max(0.0, min(1.0, sig.posture_instability_score)),
    }


def _softmax(values: dict[str, float]) -> dict[str, float]:
    m = max(values.values())
    exp = {k: math.exp(v - m) for k, v in values.items()}
    z = sum(exp.values())
    return {k: v / z for k, v in exp.items()}


class CelegansTriageNet:
    """Fixed-topology, fixed-weight triage classifier."""

    def classify(self, sig: CasualtySignature) -> str:
        return self.activate(sig).priority

    def activate(self, sig: CasualtySignature) -> NetActivation:
        sensory = _sensory_from_signature(sig)

        interneuron_raw: dict[str, float] = {}
        for inter, weights in _W_SENSORY_TO_INTER.items():
            interneuron_raw[inter] = sum(
                weights[s] * sensory[s] for s in _SENSORY
            )
        interneuron = {k: _activate(v) for k, v in interneuron_raw.items()}

        motor_raw: dict[str, float] = {}
        for motor_name, motor_weights in _W_INTER_TO_MOTOR.items():
            motor_raw[motor_name] = _MOTOR_BIAS[motor_name] + sum(
                motor_weights[i] * interneuron[i] for i in _INTERNEURONS
            )
        motor = _softmax(motor_raw)

        priority = max(motor, key=lambda k: motor[k])
        return NetActivation(
            sensory=sensory,
            interneuron=interneuron,
            motor=motor,
            priority=priority,
        )

    @staticmethod
    def n_parameters() -> int:
        """How many hand-authored weights live in this network."""
        total = sum(len(row) for row in _W_SENSORY_TO_INTER.values())
        total += sum(len(row) for row in _W_INTER_TO_MOTOR.values())
        total += len(_MOTOR_BIAS)
        return total
