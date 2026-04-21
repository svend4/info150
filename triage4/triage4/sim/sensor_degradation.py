"""Sensor-degradation simulator.

Part of triage4 Phase 7. Reproducibly degrades a ``CasualtySignature`` to
emulate adverse field conditions (noise, low visibility, partial occlusion)
so triage pipelines can be tested for robustness before real hardware.

The degradation is deterministic when seeded. It intentionally does not
degrade the body_region_polygons — those come from a separate perception
layer whose own degradation is handled there.
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass

from triage4.core.models import CasualtySignature


@dataclass
class DegradationConfig:
    noise_sigma: float = 0.05
    occlusion_prob: float = 0.0
    visibility_drop: float = 0.0
    drop_breathing_prob: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.noise_sigma <= 1.0:
            raise ValueError(
                f"noise_sigma must be in [0, 1], got {self.noise_sigma}"
            )
        if not 0.0 <= self.occlusion_prob <= 1.0:
            raise ValueError(
                f"occlusion_prob must be in [0, 1], got {self.occlusion_prob}"
            )
        if not 0.0 <= self.visibility_drop <= 1.0:
            raise ValueError(
                f"visibility_drop must be in [0, 1], got {self.visibility_drop}"
            )
        if not 0.0 <= self.drop_breathing_prob <= 1.0:
            raise ValueError(
                f"drop_breathing_prob must be in [0, 1], "
                f"got {self.drop_breathing_prob}"
            )


class SensorDegradationSimulator:
    """Deterministic signature degradation for robustness testing."""

    def __init__(self, cfg: DegradationConfig | None = None, seed: int | None = 0):
        self.cfg = cfg or DegradationConfig()
        self._rng = random.Random(seed)

    def apply(self, sig: CasualtySignature) -> CasualtySignature:
        cfg = self.cfg
        out = copy.deepcopy(sig)

        out.bleeding_visual_score = _clamp(
            out.bleeding_visual_score + self._rng.gauss(0.0, cfg.noise_sigma)
        )
        out.perfusion_drop_score = _clamp(
            out.perfusion_drop_score + self._rng.gauss(0.0, cfg.noise_sigma)
        )
        out.thermal_asymmetry_score = _clamp(
            out.thermal_asymmetry_score + self._rng.gauss(0.0, cfg.noise_sigma)
        )
        out.chest_motion_fd = _clamp(
            out.chest_motion_fd + self._rng.gauss(0.0, cfg.noise_sigma)
        )
        out.posture_instability_score = _clamp(
            out.posture_instability_score + self._rng.gauss(0.0, cfg.noise_sigma)
        )

        if cfg.drop_breathing_prob > 0.0 and self._rng.random() < cfg.drop_breathing_prob:
            out.breathing_curve = []

        if cfg.occlusion_prob > 0.0 and self._rng.random() < cfg.occlusion_prob:
            # Occlusion masks one random part of the observation.
            channel = self._rng.choice(
                [
                    "bleeding_visual_score",
                    "perfusion_drop_score",
                    "thermal_asymmetry_score",
                    "chest_motion_fd",
                    "posture_instability_score",
                ]
            )
            setattr(out, channel, 0.0)

        out.visibility_score = _clamp(
            out.visibility_score - cfg.visibility_drop
        )

        return out

    def apply_many(self, sigs: list[CasualtySignature]) -> list[CasualtySignature]:
        return [self.apply(s) for s in sigs]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
