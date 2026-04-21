from __future__ import annotations


def breath_signal(priority_hint: str) -> list[float]:
    if priority_hint == "immediate":
        return [0.01, 0.02, 0.01, 0.02, 0.01, 0.02]
    if priority_hint == "delayed":
        return [0.10, 0.13, 0.11, 0.14, 0.12, 0.13]
    return [0.22, 0.26, 0.24, 0.27, 0.25, 0.28]


def bleeding_inputs(priority_hint: str) -> tuple[float, float, float]:
    if priority_hint == "immediate":
        return 0.95, 0.55, 0.45
    if priority_hint == "delayed":
        return 0.42, 0.18, 0.15
    return 0.08, 0.05, 0.03


def perfusion_series(priority_hint: str) -> list[float]:
    if priority_hint == "immediate":
        return [0.82, 0.60, 0.35, 0.20]
    if priority_hint == "delayed":
        return [0.75, 0.65, 0.55, 0.50]
    return [0.70, 0.68, 0.67, 0.69]
