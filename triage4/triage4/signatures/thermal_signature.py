"""Thermal anomaly signature.

Part of triage4 Phase 7 (multimodal). Extracts a compact thermal
descriptor from a small thermal patch over a casualty's torso / face.

Triage use case:
- raised local temperature over a wound region → possible infection /
  inflammation;
- focal cold spot on a limb → possible perfusion loss;
- overall temperature drop compared to environment → possible shock.

The extractor is intentionally simple and deterministic: mean / std /
hotspot fraction / thermal gradient magnitude. The confidence depends on
patch size and dynamic range so downstream fusion can discount noisy
thermal frames.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np


class ThermalSignatureExtractor:
    """Simulation-first thermal anomaly descriptor."""

    def __init__(self, hotspot_z: float = 1.5) -> None:
        """``hotspot_z`` = z-score above which a pixel counts as hotspot."""
        if hotspot_z <= 0.0:
            raise ValueError(f"hotspot_z must be > 0, got {hotspot_z}")
        self.hotspot_z = float(hotspot_z)

    def extract(self, thermal_patch: Iterable[Iterable[float]]) -> dict:
        arr = np.asarray(list(thermal_patch), dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.size == 0:
            return {
                "thermal_asymmetry_score": 0.0,
                "mean_temperature_proxy": 0.0,
                "hotspot_fraction": 0.0,
                "gradient_magnitude": 0.0,
                "quality_score": 0.0,
            }

        mean = float(arr.mean())
        std = float(arr.std())
        dynamic_range = float(arr.max() - arr.min())

        if std > 1e-12:
            z = (arr - mean) / std
            hotspot_fraction = float((z > self.hotspot_z).mean())
        else:
            hotspot_fraction = 0.0

        if arr.shape[0] >= 2 and arr.shape[1] >= 2:
            gy = np.gradient(arr, axis=0)
            gx = np.gradient(arr, axis=1)
            grad_mag = float(np.sqrt(gx ** 2 + gy ** 2).mean())
        else:
            grad_mag = 0.0

        # Asymmetry: the hotspot fraction weighted by normalised gradient.
        # Values in [0, 1]; saturates at ~0.5 gradient and ~0.2 hotspot fraction.
        asymmetry = min(
            1.0, hotspot_fraction * 3.0 + min(1.0, grad_mag * 2.0) * 0.5
        )

        quality = min(1.0, max(0.2, 0.3 + dynamic_range))

        return {
            "thermal_asymmetry_score": round(asymmetry, 3),
            "mean_temperature_proxy": round(mean, 3),
            "hotspot_fraction": round(hotspot_fraction, 3),
            "gradient_magnitude": round(grad_mag, 3),
            "quality_score": round(quality, 3),
        }
