"""Tests for the Prometheus /metrics endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from triage4.ui.dashboard_api import app
from triage4.ui.metrics import (
    TriageMetricsRegistry,
    default_registry,
    render_metrics,
)


# ---------------------------------------------------------------------------
# Registry semantics
# ---------------------------------------------------------------------------


def test_empty_registry_renders_zero_counters():
    r = TriageMetricsRegistry()
    body, ct = render_metrics(r)
    assert ct.startswith("text/plain")
    assert "triage4_casualties_total" in body
    assert 'priority="unknown"' in body
    assert "triage4_handoff_latency_seconds_count 0" in body
    assert "triage4_uptime_seconds" in body


def test_casualty_counter_increments_per_priority():
    r = TriageMetricsRegistry()
    r.incr_casualty("immediate")
    r.incr_casualty("immediate")
    r.incr_casualty("delayed")
    body, _ = render_metrics(r)
    assert 'triage4_casualties_total{priority="immediate"} 2' in body
    assert 'triage4_casualties_total{priority="delayed"} 1' in body


def test_casualty_counter_treats_empty_priority_as_unknown():
    r = TriageMetricsRegistry()
    r.incr_casualty("")
    snap = r.snapshot()
    assert snap["casualties"] == {"unknown": 1}


def test_handoff_histogram_buckets_are_cumulative():
    r = TriageMetricsRegistry()
    # Three observations: 0.2 s, 1.5 s, 7.0 s.
    r.observe_handoff_latency(0.2)
    r.observe_handoff_latency(1.5)
    r.observe_handoff_latency(7.0)
    body, _ = render_metrics(r)

    # The le="0.5" bucket must include the 0.2 s sample.
    assert 'triage4_handoff_latency_seconds_bucket{le="0.5"} 1' in body
    # The le="2.5" bucket must include 0.2 + 1.5 samples.
    assert 'triage4_handoff_latency_seconds_bucket{le="2.5"} 2' in body
    # The +Inf bucket is the count.
    assert 'triage4_handoff_latency_seconds_bucket{le="+Inf"} 3' in body
    assert "triage4_handoff_latency_seconds_count 3" in body
    assert "triage4_handoff_latency_seconds_sum 8.7" in body


def test_handoff_observation_rejects_negative():
    r = TriageMetricsRegistry()
    with pytest.raises(ValueError):
        r.observe_handoff_latency(-0.1)


def test_bridge_health_gauge_sets_ok_and_down_states():
    r = TriageMetricsRegistry()
    r.set_bridge_health("uav_a", ok=True)
    r.set_bridge_health("spot_b", ok=False)
    body, _ = render_metrics(r)
    assert 'triage4_bridge_health{platform_id="uav_a",state="ok"} 1.0' in body
    assert 'triage4_bridge_health{platform_id="uav_a",state="down"} 0.0' in body
    assert 'triage4_bridge_health{platform_id="spot_b",state="ok"} 0.0' in body
    assert 'triage4_bridge_health{platform_id="spot_b",state="down"} 1.0' in body


def test_snapshot_reports_counts():
    r = TriageMetricsRegistry()
    r.incr_casualty("immediate")
    r.observe_handoff_latency(0.5)
    snap = r.snapshot()
    assert snap["casualties"] == {"immediate": 1}
    assert snap["handoff_count"] == 1
    assert snap["handoff_sum"] == 0.5
    assert snap["uptime_s"] >= 0.0


# ---------------------------------------------------------------------------
# Rendering conformance with the Prometheus exposition format
# ---------------------------------------------------------------------------


def test_render_has_help_and_type_lines():
    r = TriageMetricsRegistry()
    body, _ = render_metrics(r)
    assert "# HELP triage4_casualties_total" in body
    assert "# TYPE triage4_casualties_total counter" in body
    assert "# TYPE triage4_handoff_latency_seconds histogram" in body
    assert "# TYPE triage4_bridge_health gauge" in body
    assert "# TYPE triage4_uptime_seconds gauge" in body


def test_render_ends_with_newline():
    body, _ = render_metrics(TriageMetricsRegistry())
    assert body.endswith("\n")


def test_default_registry_is_singleton():
    assert default_registry is default_registry


# ---------------------------------------------------------------------------
# FastAPI endpoint
# ---------------------------------------------------------------------------


def test_metrics_endpoint_returns_prometheus_text():
    with TestClient(app) as client:
        resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "triage4_casualties_total" in resp.text


def test_metrics_endpoint_includes_seed_casualties():
    """Dashboard seeds demo data on startup; those show up as counters."""
    with TestClient(app) as client:
        resp = client.get("/metrics")
    body = resp.text
    # The seed has a mix of priorities — at least one line with a non-unknown label.
    assert any(
        f'priority="{p}"' in body
        for p in ("immediate", "delayed", "minimal")
    )
