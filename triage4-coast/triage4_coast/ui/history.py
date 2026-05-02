"""SQLite-backed time-series store for coast channel scores.

Append-only table; one row per (timestamp, zone_id, channel, value).
Retention is callers' responsibility — caller can call
``purge_older_than()`` periodically.

Default DB path is ``~/.triage4-coast/history.sqlite`` so a fresh
checkout doesn't accidentally write to the repo. Overrideable via
the ``TRIAGE4_COAST_HISTORY_DB`` env var.
"""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


_DEFAULT_DB_PATH = Path.home() / ".triage4-coast" / "history.sqlite"


def _db_path() -> Path:
    override = os.environ.get("TRIAGE4_COAST_HISTORY_DB")
    if override:
        return Path(override)
    return _DEFAULT_DB_PATH


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS coast_history (
                ts_unix REAL NOT NULL,
                zone_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                value REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_coast_history_zone_ts
            ON coast_history (zone_id, ts_unix)
        """)
        yield conn
        conn.commit()
    finally:
        conn.close()


def record_scores(
    *,
    zone_id: str,
    channels: dict[str, float],
    ts_unix: float | None = None,
) -> None:
    """Append one row per channel for one zone at ``ts_unix``."""
    if not zone_id:
        raise ValueError("zone_id must not be empty")
    ts = ts_unix if ts_unix is not None else time.time()
    rows = [(ts, zone_id, ch, float(v)) for ch, v in channels.items()]
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO coast_history (ts_unix, zone_id, channel, value) "
            "VALUES (?, ?, ?, ?)",
            rows,
        )


def fetch_history(
    *,
    zone_id: str,
    channel: str,
    since_unix: float | None = None,
    limit: int = 1000,
) -> list[tuple[float, float]]:
    """Return ``[(ts_unix, value), ...]`` ordered oldest → newest."""
    if not zone_id:
        raise ValueError("zone_id must not be empty")
    if not channel:
        raise ValueError("channel must not be empty")
    if limit <= 0:
        raise ValueError("limit must be positive")
    cutoff = since_unix if since_unix is not None else 0.0
    with _connect() as conn:
        cur = conn.execute(
            "SELECT ts_unix, value FROM coast_history "
            "WHERE zone_id = ? AND channel = ? AND ts_unix >= ? "
            "ORDER BY ts_unix ASC LIMIT ?",
            (zone_id, channel, cutoff, int(limit)),
        )
        return [(float(ts), float(v)) for ts, v in cur.fetchall()]


def purge_older_than(*, max_age_s: float) -> int:
    """Delete rows older than ``max_age_s`` seconds. Returns row count."""
    if max_age_s <= 0:
        raise ValueError("max_age_s must be positive")
    cutoff = time.time() - float(max_age_s)
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM coast_history WHERE ts_unix < ?", (cutoff,),
        )
        return cur.rowcount


def reset() -> None:
    """Drop and recreate the table. Test-only."""
    with _connect() as conn:
        conn.execute("DROP TABLE IF EXISTS coast_history")


__all__ = [
    "fetch_history",
    "purge_older_than",
    "record_scores",
    "reset",
]
