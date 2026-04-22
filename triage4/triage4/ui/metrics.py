"""Prometheus-format ``/metrics`` endpoint, stdlib-only.

Addresses the open question from ``docs/DEPLOYMENT.md §9``. Exposes
a minimal set of triage-relevant metrics in the Prometheus text
exposition format, so any standard scrape target (Prometheus,
Victoria Metrics, OpenTelemetry Collector) can ingest them.

No ``prometheus_client`` dependency — the exposition format is
small enough to produce directly. Three metric families:

- ``triage4_casualties_total{priority="..."}`` — Counter per
  priority band (immediate / delayed / minimal / unknown).
- ``triage4_handoff_latency_seconds`` — Histogram with fixed buckets.
- ``triage4_bridge_health{platform_id="...",state="..."}`` — Gauge.

The module is intentionally simple: one in-memory registry, no
label-cardinality explosion, no persistence. A dashboard restart
resets counters — which is fine for a decision-support tool where
aggregation lives in the upstream scraper.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


_CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

# Fixed bucket set for handoff latency. Picked for triage timing:
# sub-second → platform-level overhead; 10 s → reasonable medic
# reaction; > 30 s → something went wrong.
_LATENCY_BUCKETS_S = (0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)


@dataclass
class _Histogram:
    buckets: dict[float, int] = field(default_factory=dict)
    sum: float = 0.0
    count: int = 0

    def observe(self, value: float) -> None:
        self.sum += float(value)
        self.count += 1
        for ub in _LATENCY_BUCKETS_S:
            if value <= ub:
                self.buckets[ub] = self.buckets.get(ub, 0) + 1


class TriageMetricsRegistry:
    """In-memory metric registry. Single-writer, single-reader."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._casualties: dict[str, int] = {}
        self._handoff_hist: _Histogram = _Histogram()
        self._bridge_health: dict[tuple[str, str], float] = {}
        self._start_ts = time.time()

    # -- counters --------------------------------------------------------

    def incr_casualty(self, priority: str, *, n: int = 1) -> None:
        priority = priority if priority else "unknown"
        with self._lock:
            self._casualties[priority] = self._casualties.get(priority, 0) + int(n)

    def observe_handoff_latency(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("handoff latency cannot be negative")
        with self._lock:
            self._handoff_hist.observe(float(seconds))

    def set_bridge_health(self, platform_id: str, *, ok: bool) -> None:
        with self._lock:
            self._bridge_health[(platform_id, "ok")] = 1.0 if ok else 0.0
            self._bridge_health[(platform_id, "down")] = 0.0 if ok else 1.0

    # -- snapshot helpers (for tests) -----------------------------------

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "casualties": dict(self._casualties),
                "handoff_count": self._handoff_hist.count,
                "handoff_sum": self._handoff_hist.sum,
                "bridge_health": dict(self._bridge_health),
                "uptime_s": time.time() - self._start_ts,
            }

    # -- exposition -----------------------------------------------------

    def render(self) -> str:
        with self._lock:
            casualties = dict(self._casualties)
            hist = _Histogram(
                buckets=dict(self._handoff_hist.buckets),
                sum=self._handoff_hist.sum,
                count=self._handoff_hist.count,
            )
            bridge = dict(self._bridge_health)
            uptime = time.time() - self._start_ts

        lines: list[str] = []

        lines.append("# HELP triage4_casualties_total Triage decisions per priority band.")
        lines.append("# TYPE triage4_casualties_total counter")
        if not casualties:
            lines.append('triage4_casualties_total{priority="unknown"} 0')
        for prio in sorted(casualties):
            lines.append(
                f'triage4_casualties_total{{priority="{prio}"}} {casualties[prio]}'
            )

        lines.append("# HELP triage4_handoff_latency_seconds Latency from decision to medic handoff.")
        lines.append("# TYPE triage4_handoff_latency_seconds histogram")
        cumulative = 0
        for ub in _LATENCY_BUCKETS_S:
            cumulative = max(cumulative, hist.buckets.get(ub, 0))
            lines.append(
                f'triage4_handoff_latency_seconds_bucket{{le="{ub}"}} {cumulative}'
            )
        lines.append(
            f'triage4_handoff_latency_seconds_bucket{{le="+Inf"}} {hist.count}'
        )
        lines.append(f"triage4_handoff_latency_seconds_sum {hist.sum}")
        lines.append(f"triage4_handoff_latency_seconds_count {hist.count}")

        lines.append("# HELP triage4_bridge_health Per-platform bridge health (1 = healthy, 0 = not).")
        lines.append("# TYPE triage4_bridge_health gauge")
        if not bridge:
            lines.append('triage4_bridge_health{platform_id="none",state="ok"} 0')
        for (pid, state) in sorted(bridge):
            lines.append(
                f'triage4_bridge_health{{platform_id="{pid}",state="{state}"}} '
                f'{bridge[(pid, state)]}'
            )

        lines.append("# HELP triage4_uptime_seconds Seconds since the registry was created.")
        lines.append("# TYPE triage4_uptime_seconds gauge")
        lines.append(f"triage4_uptime_seconds {uptime:.3f}")

        return "\n".join(lines) + "\n"


# Process-level default registry. Modules that emit metrics import
# this, matching the prometheus_client convention without the dep.
default_registry = TriageMetricsRegistry()


def render_metrics(registry: TriageMetricsRegistry | None = None) -> tuple[str, str]:
    """Return ``(body, content_type)`` for a ``/metrics`` response."""
    r = registry or default_registry
    return r.render(), _CONTENT_TYPE
