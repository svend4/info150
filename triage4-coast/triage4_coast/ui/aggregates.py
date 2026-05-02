"""Hourly aggregates over the SQLite history store.

Used by the ops-console widgets (StackedTrend, TimeStripChart) to
render trends without re-fetching every raw point.
"""

from __future__ import annotations

import time

from . import history


def hourly_zone_density(
    *,
    zone_id: str,
    channel: str = "overall",
    hours: int = 24,
) -> list[dict[str, float]]:
    """Return ``[{hour_ago, mean_value, n_samples}, ...]`` for one zone.

    Each bucket covers one hour of wall-clock; ``hour_ago=0`` is the
    most recent hour. Buckets with zero samples are omitted.
    """
    if hours <= 0 or hours > 24 * 30:
        raise ValueError("hours must be in (0, 720]")
    if not zone_id:
        raise ValueError("zone_id must not be empty")

    now = time.time()
    since = now - hours * 3600.0
    rows = history.fetch_history(
        zone_id=zone_id, channel=channel, since_unix=since, limit=100_000,
    )
    if not rows:
        return []

    buckets: dict[int, list[float]] = {}
    for ts, value in rows:
        bucket = int((now - ts) // 3600)
        buckets.setdefault(bucket, []).append(value)

    out: list[dict[str, float]] = []
    for hour_ago in sorted(buckets.keys()):
        vals = buckets[hour_ago]
        out.append({
            "hour_ago": float(hour_ago),
            "mean_value": sum(vals) / len(vals),
            "n_samples": float(len(vals)),
        })
    return out


def coast_level_counts_over_time(
    *,
    zone_ids: list[str],
    hours: int = 4,
    bucket_minutes: int = 5,
) -> list[dict[str, float]]:
    """Bucketize ok/watch/urgent counts across all zones.

    Inferred from each zone's ``overall`` channel value:
        overall < 0.45  -> urgent
        overall < 0.65  -> watch
        else            -> ok

    Returns one row per bucket: ``{ts_unix, ok, watch, urgent}``,
    oldest first.
    """
    if hours <= 0 or hours > 24 * 30:
        raise ValueError("hours must be in (0, 720]")
    if bucket_minutes <= 0 or bucket_minutes > 60 * 24:
        raise ValueError("bucket_minutes must be in (0, 1440]")
    if not zone_ids:
        return []

    now = time.time()
    since = now - hours * 3600.0
    bucket_sec = bucket_minutes * 60.0

    # Per zone, gather (ts, overall) within the window.
    zone_series: dict[str, list[tuple[float, float]]] = {}
    for z in zone_ids:
        zone_series[z] = history.fetch_history(
            zone_id=z, channel="overall", since_unix=since, limit=100_000,
        )

    buckets: dict[float, dict[str, int]] = {}
    for z, series in zone_series.items():
        # For each bucket, take the latest overall in that bucket as
        # this zone's state at that time.
        per_bucket: dict[float, float] = {}
        for ts, v in series:
            b = since + (int((ts - since) // bucket_sec)) * bucket_sec
            per_bucket[b] = v   # later overwrites earlier within bucket
        for b, v in per_bucket.items():
            level = (
                "urgent" if v < 0.45
                else "watch" if v < 0.65
                else "ok"
            )
            row = buckets.setdefault(b, {"ok": 0, "watch": 0, "urgent": 0})
            row[level] += 1

    out: list[dict[str, float]] = []
    for b in sorted(buckets.keys()):
        row = buckets[b]
        out.append({
            "ts_unix": float(b),
            "ok": float(row["ok"]),
            "watch": float(row["watch"]),
            "urgent": float(row["urgent"]),
        })
    return out


__all__ = ["coast_level_counts_over_time", "hourly_zone_density"]
