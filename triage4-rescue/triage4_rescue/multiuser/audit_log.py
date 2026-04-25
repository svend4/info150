"""Append-only audit log for dispatcher actions.

Two backends, same interface:

- ``AuditLog()`` — in-memory list. Cheap, no persistence. Suitable for
  tests, demos, and short-lived deployments.
- ``AuditLog(db_path=...)`` — SQLite-backed. Survives process restart.
  Schema is created on first use (single ``audit_entries`` table; no
  migration plan because the schema is final).

The row shape is generic on purpose (action / actor / target /
payload). It is **not** the place to store incident *content* — that
belongs in ``IncidentReport`` instances. Audit-log entries describe
**what someone did**, not what the incident was.

Privacy note: callers must not place identifiable casualty / patient
information into ``payload``. Audit content is meant to be safe to
share with regulators and post-incident reviewers; PHI / PII would
cross the boundary documented in ``triage4-rescue/docs/PHILOSOPHY.md``.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuditEntry:
    entry_id: int
    timestamp: float
    action: str
    actor_user_id: str
    actor_role: str
    target_type: str
    target_id: str
    payload: dict[str, Any] = field(default_factory=dict)


class AuditLog:
    """Thread-safe append-only audit log.

    ``db_path=None`` keeps everything in memory. A path opens (or
    creates) a SQLite file with one ``audit_entries`` table.
    """

    _SCHEMA = """
        CREATE TABLE IF NOT EXISTS audit_entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            action TEXT NOT NULL,
            actor_user_id TEXT NOT NULL DEFAULT '',
            actor_role TEXT NOT NULL DEFAULT '',
            target_type TEXT NOT NULL DEFAULT '',
            target_id TEXT NOT NULL DEFAULT '',
            payload TEXT NOT NULL DEFAULT '{}'
        );
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._lock = threading.Lock()
        self._db_path: Path | None = Path(db_path) if db_path else None
        self._mem: list[AuditEntry] = []
        self._next_id: int = 1
        if self._db_path is not None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self._db_path) as conn:
                conn.executescript(self._SCHEMA)

    # -- writes -------------------------------------------------------

    def append(
        self,
        action: str,
        actor_user_id: str = "",
        actor_role: str = "",
        target_type: str = "",
        target_id: str = "",
        payload: dict[str, Any] | None = None,
    ) -> AuditEntry:
        if not action:
            raise ValueError("audit action must not be empty")
        ts = time.time()
        body = dict(payload or {})
        with self._lock:
            if self._db_path is None:
                entry = AuditEntry(
                    entry_id=self._next_id,
                    timestamp=ts,
                    action=action,
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    target_type=target_type,
                    target_id=target_id,
                    payload=body,
                )
                self._next_id += 1
                self._mem.append(entry)
                return entry
            # SQLite path
            with sqlite3.connect(self._db_path) as conn:
                cur = conn.execute(
                    "INSERT INTO audit_entries "
                    "(timestamp, action, actor_user_id, actor_role, "
                    " target_type, target_id, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        ts,
                        action,
                        actor_user_id,
                        actor_role,
                        target_type,
                        target_id,
                        json.dumps(body, sort_keys=True),
                    ),
                )
                entry_id = int(cur.lastrowid or 0)
                conn.commit()
            return AuditEntry(
                entry_id=entry_id,
                timestamp=ts,
                action=action,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                target_type=target_type,
                target_id=target_id,
                payload=body,
            )

    # -- reads --------------------------------------------------------

    def list(
        self,
        limit: int = 100,
        action: str | None = None,
    ) -> list[AuditEntry]:
        if limit <= 0:
            return []
        with self._lock:
            if self._db_path is None:
                rows = list(self._mem)
                if action is not None:
                    rows = [r for r in rows if r.action == action]
                return list(reversed(rows))[:limit]
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                if action is None:
                    cur = conn.execute(
                        "SELECT * FROM audit_entries "
                        "ORDER BY entry_id DESC LIMIT ?",
                        (limit,),
                    )
                else:
                    cur = conn.execute(
                        "SELECT * FROM audit_entries "
                        "WHERE action = ? "
                        "ORDER BY entry_id DESC LIMIT ?",
                        (action, limit),
                    )
                return [self._row_to_entry(row) for row in cur.fetchall()]

    def __len__(self) -> int:
        with self._lock:
            if self._db_path is None:
                return len(self._mem)
            with sqlite3.connect(self._db_path) as conn:
                cur = conn.execute("SELECT COUNT(*) FROM audit_entries")
                return int(cur.fetchone()[0])

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> AuditEntry:
        return AuditEntry(
            entry_id=int(row["entry_id"]),
            timestamp=float(row["timestamp"]),
            action=str(row["action"]),
            actor_user_id=str(row["actor_user_id"]),
            actor_role=str(row["actor_role"]),
            target_type=str(row["target_type"]),
            target_id=str(row["target_id"]),
            payload=json.loads(str(row["payload"])),
        )
