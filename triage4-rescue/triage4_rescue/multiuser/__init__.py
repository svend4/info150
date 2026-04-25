"""Multi-user / multi-shift coordination layer for triage4-rescue.

Pilot adoption of architectural ideas from `triage4_repo_v13.zip` —
see `V13_REUSE_MAP.md` at the monorepo root for the per-sibling reuse
policy. Specifically:

- v13's `auth/` (session_manager + policy_engine) → ``RescueRole`` +
  ``SessionManager`` + ``PolicyEngine`` here, with rescue-specific
  role + action vocabulary (``viewer / dispatcher / incident_commander
  / admin``, actions like ``incident:log``, ``responder:assign``).
- v13's `repositories/audit_repository.py` → ``AuditLog`` here, an
  append-only journal of dispatcher actions for post-incident review.
- v13's `jobs/async_queue.py` + `worker_loop.py` → ``AsyncJobQueue``
  here, for batch incident-summary processing.

This is **copy-fork**, not import. Nothing in this subpackage depends
on v13 source. Each module is sized for the rescue domain and free to
diverge from v13's shape.

Default storage is in-memory. Persistence is opt-in: an ``AuditLog``
can be constructed with a SQLite path; ``SessionManager`` stays
in-memory because sessions are short-lived (one shift).
"""

from __future__ import annotations

from .actions import (
    DEFAULT_ROLE_ACTIONS,
    RescueAction,
    VALID_ACTIONS,
)
from .audit_log import AuditEntry, AuditLog
from .jobs import AsyncJobQueue, BackgroundWorkerLoop
from .policy_engine import PolicyEngine
from .roles import ROLE_ORDER, RescueRole, validate_role
from .session_manager import Session, SessionManager, User

__all__ = [
    "AsyncJobQueue",
    "AuditEntry",
    "AuditLog",
    "BackgroundWorkerLoop",
    "DEFAULT_ROLE_ACTIONS",
    "PolicyEngine",
    "ROLE_ORDER",
    "RescueAction",
    "RescueRole",
    "Session",
    "SessionManager",
    "User",
    "VALID_ACTIONS",
    "validate_role",
]
