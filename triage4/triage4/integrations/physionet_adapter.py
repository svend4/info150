"""PhysioNet / WFDB record adapter.

Part of Phase 9b. Loads a PhysioNet-style record (header ``.hea`` + one
or more ``.dat`` signal files) and exposes the channels triage4 cares
about — respiration and PPG / pulse — as plain numpy arrays that feed
straight into :class:`VitalsEstimator`.

Real WFDB parsing requires the optional ``wfdb`` package. To keep
triage4's default install light, this module supports three modes:

- ``load_dict(...)`` — feed an in-memory dict (channel name → array +
  sample rate). Works without any external SDK. Used by tests and by
  ad-hoc research notebooks.
- ``load_wfdb(...)`` — optional lazy factory that imports ``wfdb`` and
  reads a record file. Raises :class:`PhysioNetUnavailable` with
  install instructions when the SDK is missing.
- ``PhysioNetRecord`` — the contract downstream code consumes, so the
  two loaders are drop-in swappable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


class PhysioNetUnavailable(RuntimeError):
    """Raised when the real-backend factory can't find ``wfdb``."""


@dataclass
class PhysioNetRecord:
    """One loaded record — channels, sample-rate and metadata.

    The channel ``pulse`` feeds ``VitalsEstimator.perfusion_series`` and
    ``respiration`` feeds the ``breathing_curve`` argument.
    """

    record_id: str
    fs_hz: float
    pulse: np.ndarray
    respiration: np.ndarray
    annotations: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.fs_hz <= 0:
            raise ValueError(f"fs_hz must be > 0, got {self.fs_hz}")
        if self.pulse.ndim != 1:
            raise ValueError("pulse must be a 1-D array")
        if self.respiration.ndim != 1:
            raise ValueError("respiration must be a 1-D array")


def load_dict(
    record_id: str,
    fs_hz: float,
    pulse: np.ndarray | list[float],
    respiration: np.ndarray | list[float],
    annotations: dict | None = None,
) -> PhysioNetRecord:
    """In-memory constructor — no SDK required."""
    return PhysioNetRecord(
        record_id=str(record_id),
        fs_hz=float(fs_hz),
        pulse=np.asarray(pulse, dtype=np.float64),
        respiration=np.asarray(respiration, dtype=np.float64),
        annotations=dict(annotations or {}),
    )


def load_wfdb(record_path: str) -> PhysioNetRecord:  # pragma: no cover
    """Lazy-load ``wfdb`` and read a PhysioNet record.

    The adapter looks for signal names that are reasonable matches to
    our two expected channels and raises if it can't find them. In the
    sandbox environment the ``wfdb`` package is not installed, so this
    path is exercised only when users opt into the extra.
    """
    try:
        import wfdb  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise PhysioNetUnavailable(
            "wfdb is not installed. Install with 'pip install wfdb' or use "
            "load_dict(...) for in-memory records (tests / notebooks)."
        ) from exc

    record = wfdb.rdrecord(record_path)
    sig_names = [name.lower() for name in record.sig_name]
    fs_hz = float(record.fs)

    def _find_channel(substrings: list[str]) -> np.ndarray:
        for i, name in enumerate(sig_names):
            for sub in substrings:
                if sub in name:
                    return np.asarray(record.p_signal[:, i], dtype=np.float64)
        raise ValueError(
            f"no channel matching {substrings} in {record_path} "
            f"(available: {sig_names})"
        )

    pulse = _find_channel(["ppg", "pleth", "bp", "abp"])
    respiration = _find_channel(["resp", "imp"])

    return PhysioNetRecord(
        record_id=record.record_name,
        fs_hz=fs_hz,
        pulse=pulse,
        respiration=respiration,
        annotations={"sig_names": record.sig_name},
    )
