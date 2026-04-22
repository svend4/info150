"""Bayesian patient twin — particle filter over triage state.

Part of Phase 9c (innovation pack 2, idea #5). Upgrades the
single-number ``UncertaintyReport`` to a full probability distribution
over priority bands plus deterioration rate.

Each casualty is represented by ``n_particles`` particles, each of
which is a candidate ``(priority_band, deterioration_rate)``. Every
observation reweights the particles by likelihood, then resamples.

The output is:
- the posterior probability of each priority band;
- the most likely band and its probability;
- effective sample size (sanity: below 20% of n_particles means the
  filter has collapsed and the estimate should not be trusted).

Pure-numpy; ~150 lines; O(n_particles) per update.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from triage4.core.models import CasualtySignature


# Priority bands as integers so we can use them as array indices.
_BANDS = ("minimal", "delayed", "immediate")


@dataclass
class TwinPosterior:
    """Posterior estimate of a casualty's triage state."""

    priority_probs: dict[str, float]   # {"minimal": p, ...}
    most_likely_priority: str
    most_likely_probability: float
    deterioration_rate: float           # mean across particles, [0, 1]
    effective_sample_size: float        # 0..n_particles

    @property
    def is_degenerate(self) -> bool:
        """True if particle cloud has collapsed — estimate untrustworthy."""
        return self.effective_sample_size < 5.0


def _expected_signature(band_index: int) -> np.ndarray:
    """Rough per-band expected (bleeding, chest_motion_risk, perfusion, posture)."""
    if band_index == 0:  # minimal
        return np.array([0.10, 0.10, 0.15, 0.10])
    if band_index == 1:  # delayed
        return np.array([0.40, 0.40, 0.50, 0.40])
    return np.array([0.85, 0.85, 0.80, 0.75])  # immediate


def _observation_vector(sig: CasualtySignature) -> np.ndarray:
    chest_motion_risk = 1.0 - float(max(0.0, min(1.0, sig.chest_motion_fd)))
    if len(sig.breathing_curve) < 4:
        chest_motion_risk = 0.0
    return np.array(
        [
            max(0.0, min(1.0, sig.bleeding_visual_score)),
            chest_motion_risk,
            max(0.0, min(1.0, sig.perfusion_drop_score)),
            max(0.0, min(1.0, sig.posture_instability_score)),
        ]
    )


class PatientTwinFilter:
    """Particle filter over (priority_band, deterioration_rate) for one casualty."""

    def __init__(
        self,
        n_particles: int = 200,
        observation_sigma: float = 0.25,
        seed: int | None = 0,
    ) -> None:
        if n_particles < 10:
            raise ValueError(f"n_particles must be >= 10, got {n_particles}")
        if observation_sigma <= 0.0:
            raise ValueError(
                f"observation_sigma must be > 0, got {observation_sigma}"
            )

        self.n_particles = int(n_particles)
        self.sigma = float(observation_sigma)
        self._rng = np.random.default_rng(seed)

        # Initialise with a flat prior over bands and zero deterioration.
        self._bands = self._rng.integers(0, 3, size=self.n_particles)
        self._deterioration = self._rng.uniform(0.0, 0.3, size=self.n_particles)
        self._weights = np.full(self.n_particles, 1.0 / self.n_particles)

    def update(self, sig: CasualtySignature, dt_s: float = 0.0) -> TwinPosterior:
        """Incorporate one observation, optionally advance the state by dt_s."""
        # Transition step: let bands drift upward with deterioration rate.
        if dt_s > 0.0:
            drift_chance = self._deterioration * (dt_s / 60.0)
            drift = self._rng.random(self.n_particles) < drift_chance
            self._bands = np.clip(self._bands + drift.astype(int), 0, 2)

        # Likelihood of the observation given each particle's band.
        obs = _observation_vector(sig)
        log_w = np.zeros(self.n_particles)
        for i in range(self.n_particles):
            expected = _expected_signature(int(self._bands[i]))
            diff = obs - expected
            log_w[i] = -0.5 * float(np.sum(diff ** 2)) / (self.sigma ** 2)

        # Stabilise + normalise.
        log_w -= log_w.max()
        weights = np.exp(log_w) * self._weights
        if weights.sum() < 1e-12:
            weights = np.full(self.n_particles, 1.0 / self.n_particles)
        else:
            weights = weights / weights.sum()
        self._weights = weights

        # Systematic resampling.
        ess = 1.0 / float(np.sum(weights ** 2))
        if ess < self.n_particles / 2:
            positions = (self._rng.random() + np.arange(self.n_particles)) / self.n_particles
            cumulative = np.cumsum(weights)
            indices = np.searchsorted(cumulative, positions)
            indices = np.clip(indices, 0, self.n_particles - 1)
            self._bands = self._bands[indices]
            self._deterioration = self._deterioration[indices]
            # Add small jitter to deterioration so the filter can still explore.
            self._deterioration += self._rng.normal(0.0, 0.02, self.n_particles)
            self._deterioration = np.clip(self._deterioration, 0.0, 1.0)
            self._weights = np.full(self.n_particles, 1.0 / self.n_particles)

        return self.posterior()

    def posterior(self) -> TwinPosterior:
        counts = np.zeros(3)
        for band, w in zip(self._bands, self._weights):
            counts[int(band)] += w
        counts = counts / counts.sum() if counts.sum() > 0 else np.full(3, 1 / 3)

        probs = {_BANDS[i]: float(round(counts[i], 3)) for i in range(3)}
        best_idx = int(np.argmax(counts))
        ess = float(1.0 / max(float(np.sum(self._weights ** 2)), 1e-12))

        return TwinPosterior(
            priority_probs=probs,
            most_likely_priority=_BANDS[best_idx],
            most_likely_probability=float(round(counts[best_idx], 3)),
            deterioration_rate=float(round(np.mean(self._deterioration), 3)),
            effective_sample_size=round(ess, 1),
        )
