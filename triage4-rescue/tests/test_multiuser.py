"""Tests for triage4_rescue.multiuser.

Covers roles, actions, policy engine, session manager, audit log
(in-memory + SQLite), and the async job queue.
"""

from __future__ import annotations

import threading
import time

import pytest

from triage4_rescue.multiuser import (
    AsyncJobQueue,
    AuditLog,
    DEFAULT_ROLE_ACTIONS,
    PolicyEngine,
    ROLE_ORDER,
    SessionManager,
    VALID_ACTIONS,
    validate_role,
)


# ---------------------------------------------------------------------------
# roles
# ---------------------------------------------------------------------------


def test_role_order_is_strictly_ascending():
    levels = list(ROLE_ORDER.values())
    assert levels == sorted(levels)
    assert len(set(levels)) == len(levels)


def test_validate_role_accepts_known_role():
    assert validate_role("dispatcher") == "dispatcher"


def test_validate_role_rejects_unknown_role():
    with pytest.raises(ValueError, match="unknown rescue role"):
        validate_role("operator")  # v13 vocabulary not allowed here


# ---------------------------------------------------------------------------
# actions / DEFAULT_ROLE_ACTIONS
# ---------------------------------------------------------------------------


def test_default_grants_have_no_overlap_between_roles():
    """The grant table lists each action under exactly one role; the
    PolicyEngine composes inheritance separately."""
    seen: set[str] = set()
    for actions in DEFAULT_ROLE_ACTIONS.values():
        for a in actions:
            assert a not in seen, f"action {a!r} listed under multiple roles"
            seen.add(a)


def test_default_grants_only_use_valid_actions():
    for actions in DEFAULT_ROLE_ACTIONS.values():
        unknown = set(actions) - VALID_ACTIONS
        assert not unknown


def test_admin_grants_include_users_mutate():
    assert "users:mutate" in DEFAULT_ROLE_ACTIONS["admin"]


def test_dispatcher_cannot_close_shift_by_default():
    assert "shift:close" not in DEFAULT_ROLE_ACTIONS["dispatcher"]


# ---------------------------------------------------------------------------
# PolicyEngine
# ---------------------------------------------------------------------------


def test_policy_inheritance_admin_has_everything():
    pe = PolicyEngine()
    allowed = pe.allowed_actions("admin")
    assert allowed == VALID_ACTIONS


def test_policy_inheritance_viewer_has_only_reads():
    pe = PolicyEngine()
    allowed = pe.allowed_actions("viewer")
    assert allowed == DEFAULT_ROLE_ACTIONS["viewer"]


def test_policy_dispatcher_inherits_viewer_grants():
    pe = PolicyEngine()
    allowed = pe.allowed_actions("dispatcher")
    assert "incident:read" in allowed  # inherited from viewer
    assert "incident:log" in allowed  # own grant


def test_policy_can_returns_false_for_unknown_action():
    pe = PolicyEngine()
    assert pe.can("admin", "nuke:everything") is False


def test_policy_require_raises_on_denied_action():
    pe = PolicyEngine()
    with pytest.raises(PermissionError, match="cannot perform"):
        pe.require("dispatcher", "users:mutate")


def test_policy_require_passes_when_allowed():
    pe = PolicyEngine()
    pe.require("incident_commander", "shift:close")  # no exception


def test_policy_rejects_unknown_action_in_grant_table():
    bad = dict(DEFAULT_ROLE_ACTIONS)
    bad["dispatcher"] = frozenset({"made:up:action"})  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="unknown actions"):
        PolicyEngine(role_actions=bad)  # type: ignore[arg-type]


def test_policy_custom_grants_override():
    """Deployments can override the default vocabulary."""
    custom = dict(DEFAULT_ROLE_ACTIONS)
    custom["dispatcher"] = DEFAULT_ROLE_ACTIONS["dispatcher"] | {"shift:close"}
    pe = PolicyEngine(role_actions=custom)  # type: ignore[arg-type]
    assert pe.can("dispatcher", "shift:close") is True


# ---------------------------------------------------------------------------
# SessionManager
# ---------------------------------------------------------------------------


def test_session_manager_create_and_get_user():
    sm = SessionManager()
    user = sm.create_user("alice", role="dispatcher", display_name="Alice A.")
    assert sm.get_user("alice") == user
    assert user.role == "dispatcher"


def test_session_manager_rejects_duplicate_user():
    sm = SessionManager()
    sm.create_user("bob")
    with pytest.raises(ValueError, match="already exists"):
        sm.create_user("bob")


def test_session_manager_rejects_empty_user_id():
    sm = SessionManager()
    with pytest.raises(ValueError, match="must not be empty"):
        sm.create_user("")


def test_session_manager_rejects_unknown_role():
    sm = SessionManager()
    with pytest.raises(ValueError, match="unknown rescue role"):
        sm.create_user("carol", role="operator")


def test_session_manager_create_and_resolve_session():
    sm = SessionManager()
    sm.create_user("dan", role="incident_commander")
    sess = sm.create_session("dan")
    resolved = sm.resolve(sess.token)
    assert resolved is not None
    assert resolved.user_id == "dan"
    assert resolved.role == "incident_commander"


def test_session_manager_resolve_unknown_token_returns_none():
    sm = SessionManager()
    assert sm.resolve("totally-fake") is None
    assert sm.resolve(None) is None
    assert sm.resolve("") is None


def test_session_manager_revoke_session():
    sm = SessionManager()
    sm.create_user("eve")
    sess = sm.create_session("eve")
    assert sm.revoke(sess.token) is True
    assert sm.resolve(sess.token) is None
    # Idempotent: revoking again is a no-op returning False.
    assert sm.revoke(sess.token) is False


def test_session_manager_require_role_passes_when_high_enough():
    sm = SessionManager()
    sm.create_user("frank", role="incident_commander")
    sess = sm.create_session("frank")
    out = sm.require_role(sess.token, "dispatcher")
    assert out.user_id == "frank"


def test_session_manager_require_role_fails_when_too_low():
    sm = SessionManager()
    sm.create_user("greg", role="viewer")
    sess = sm.create_session("greg")
    with pytest.raises(PermissionError, match="insufficient"):
        sm.require_role(sess.token, "dispatcher")


def test_session_manager_require_role_fails_without_token():
    sm = SessionManager()
    with pytest.raises(PermissionError, match="missing or invalid"):
        sm.require_role(None, "viewer")
    with pytest.raises(PermissionError, match="missing or invalid"):
        sm.require_role("garbage", "viewer")


def test_session_manager_role_change_cascades_into_open_session():
    sm = SessionManager()
    sm.create_user("hank", role="viewer")
    sess = sm.create_session("hank")
    assert sess.role == "viewer"
    sm.update_role("hank", "incident_commander")
    refreshed = sm.resolve(sess.token)
    assert refreshed is not None
    assert refreshed.role == "incident_commander"


def test_session_manager_delete_user_drops_open_sessions():
    sm = SessionManager()
    sm.create_user("ivy")
    sess = sm.create_session("ivy")
    sm.delete_user("ivy")
    assert sm.resolve(sess.token) is None


def test_session_manager_tokens_are_unique():
    sm = SessionManager()
    sm.create_user("jay")
    tokens = {sm.create_session("jay").token for _ in range(50)}
    assert len(tokens) == 50


# ---------------------------------------------------------------------------
# AuditLog — in-memory
# ---------------------------------------------------------------------------


def test_audit_in_memory_append_and_list():
    log = AuditLog()
    e1 = log.append("incident:log", actor_user_id="alice", actor_role="dispatcher",
                    target_type="incident", target_id="INC-1")
    e2 = log.append("responder:assign", actor_user_id="alice",
                    actor_role="dispatcher", target_id="INC-1",
                    payload={"unit": "Engine-3"})
    rows = log.list()
    assert len(rows) == 2
    assert rows[0].entry_id == e2.entry_id  # most recent first
    assert rows[1].entry_id == e1.entry_id
    assert rows[0].payload == {"unit": "Engine-3"}


def test_audit_in_memory_filter_by_action():
    log = AuditLog()
    log.append("incident:log", actor_user_id="a", actor_role="dispatcher")
    log.append("incident:log", actor_user_id="a", actor_role="dispatcher")
    log.append("shift:close", actor_user_id="b", actor_role="incident_commander")
    only_logs = log.list(action="incident:log")
    assert len(only_logs) == 2
    assert all(e.action == "incident:log" for e in only_logs)


def test_audit_in_memory_limit_clamps_results():
    log = AuditLog()
    for i in range(20):
        log.append("incident:log", target_id=f"INC-{i}",
                   actor_user_id="a", actor_role="dispatcher")
    rows = log.list(limit=5)
    assert len(rows) == 5


def test_audit_in_memory_zero_or_negative_limit_returns_empty():
    log = AuditLog()
    log.append("incident:log", actor_user_id="a", actor_role="dispatcher")
    assert log.list(limit=0) == []
    assert log.list(limit=-1) == []


def test_audit_rejects_empty_action():
    log = AuditLog()
    with pytest.raises(ValueError, match="must not be empty"):
        log.append("")


def test_audit_in_memory_len():
    log = AuditLog()
    assert len(log) == 0
    log.append("incident:log", actor_user_id="a", actor_role="dispatcher")
    log.append("incident:log", actor_user_id="a", actor_role="dispatcher")
    assert len(log) == 2


def test_audit_assigns_monotonic_entry_ids():
    log = AuditLog()
    e1 = log.append("incident:log", actor_user_id="a", actor_role="dispatcher")
    e2 = log.append("incident:log", actor_user_id="a", actor_role="dispatcher")
    assert e2.entry_id > e1.entry_id


def test_audit_timestamps_are_recent():
    log = AuditLog()
    before = time.time()
    e = log.append("incident:log", actor_user_id="a", actor_role="dispatcher")
    after = time.time()
    assert before <= e.timestamp <= after


# ---------------------------------------------------------------------------
# AuditLog — SQLite-backed
# ---------------------------------------------------------------------------


def test_audit_sqlite_round_trip(tmp_path):
    db = tmp_path / "audit.sqlite"
    log = AuditLog(db_path=db)
    log.append("incident:log", actor_user_id="alice",
               actor_role="dispatcher", target_id="INC-1",
               payload={"note": "structure fire reported"})
    log.append("responder:assign", actor_user_id="alice",
               actor_role="dispatcher", target_id="INC-1",
               payload={"unit": "Engine-3"})
    rows = log.list()
    assert len(rows) == 2
    assert rows[0].action == "responder:assign"
    assert rows[0].payload == {"unit": "Engine-3"}


def test_audit_sqlite_persists_across_instances(tmp_path):
    db = tmp_path / "audit.sqlite"
    log_a = AuditLog(db_path=db)
    log_a.append("incident:log", actor_user_id="x", actor_role="dispatcher")
    log_b = AuditLog(db_path=db)
    assert len(log_b) == 1
    assert log_b.list()[0].actor_user_id == "x"


def test_audit_sqlite_filter_by_action(tmp_path):
    db = tmp_path / "audit.sqlite"
    log = AuditLog(db_path=db)
    log.append("incident:log", actor_user_id="a", actor_role="dispatcher")
    log.append("shift:close", actor_user_id="b",
               actor_role="incident_commander")
    log.append("incident:log", actor_user_id="a", actor_role="dispatcher")
    only_close = log.list(action="shift:close")
    assert len(only_close) == 1
    assert only_close[0].actor_user_id == "b"


def test_audit_sqlite_creates_parent_dir(tmp_path):
    db = tmp_path / "nested" / "deep" / "audit.sqlite"
    AuditLog(db_path=db)  # should not raise
    assert db.exists()


# ---------------------------------------------------------------------------
# Jobs — AsyncJobQueue + BackgroundWorkerLoop
# ---------------------------------------------------------------------------


def test_jobs_runs_callback_on_success():
    q = AsyncJobQueue()
    results: list[int] = []
    errors: list[BaseException] = []
    q.submit("J1", lambda: 42, results.append, errors.append)
    q.join()
    assert results == [42]
    assert errors == []


def test_jobs_runs_callback_on_error():
    q = AsyncJobQueue()
    results: list[int] = []
    errors: list[BaseException] = []

    def boom() -> int:
        raise RuntimeError("boom")

    q.submit("J1", boom, results.append, errors.append)
    q.join()
    assert results == []
    assert len(errors) == 1
    assert isinstance(errors[0], RuntimeError)


def test_jobs_preserves_submission_order():
    q = AsyncJobQueue()
    results: list[int] = []
    lock = threading.Lock()

    def append(value: int):
        def cb(_: object) -> None:
            with lock:
                results.append(value)
        return cb

    for i in range(10):
        q.submit(f"J{i}", lambda i=i: i, append(i), lambda _e: None)
    q.join()
    assert results == list(range(10))


def test_jobs_status_reports_started_after_first_submit():
    q = AsyncJobQueue()
    assert q.status()["started"] is False
    q.submit("J1", lambda: None, lambda _r: None, lambda _e: None)
    q.join()
    assert q.status()["started"] is True


def test_jobs_rejects_empty_job_id():
    q = AsyncJobQueue()
    with pytest.raises(ValueError, match="job_id must not be empty"):
        q.submit("", lambda: None, lambda _r: None, lambda _e: None)


def test_jobs_exception_does_not_kill_worker():
    q = AsyncJobQueue()
    results: list[int] = []
    errors: list[BaseException] = []
    q.submit("J1", lambda: (_ for _ in ()).throw(ValueError("x")),
             results.append, errors.append)
    q.submit("J2", lambda: 7, results.append, errors.append)
    q.join()
    assert results == [7]
    assert len(errors) == 1


# ---------------------------------------------------------------------------
# Integration — session + policy + audit
# ---------------------------------------------------------------------------


def test_integration_dispatcher_logs_incident_with_audit_trail():
    sm = SessionManager()
    pe = PolicyEngine()
    log = AuditLog()

    sm.create_user("alice", role="dispatcher")
    sess = sm.create_session("alice")

    # Dispatcher action — permitted.
    pe.require(sess.role, "incident:log")
    log.append("incident:log", actor_user_id=sess.user_id,
               actor_role=sess.role, target_type="incident",
               target_id="INC-42",
               payload={"summary": "Two-vehicle accident, Hwy 17"})

    rows = log.list()
    assert len(rows) == 1
    assert rows[0].actor_user_id == "alice"
    assert rows[0].actor_role == "dispatcher"


def test_integration_dispatcher_blocked_from_admin_action():
    sm = SessionManager()
    pe = PolicyEngine()
    log = AuditLog()
    sm.create_user("alice", role="dispatcher")
    sess = sm.create_session("alice")
    with pytest.raises(PermissionError):
        pe.require(sess.role, "users:mutate")
    assert len(log) == 0  # nothing logged if action denied


def test_integration_role_change_propagates_to_session():
    sm = SessionManager()
    pe = PolicyEngine()
    sm.create_user("bob", role="dispatcher")
    sess = sm.create_session("bob")
    with pytest.raises(PermissionError):
        pe.require(sess.role, "shift:close")
    sm.update_role("bob", "incident_commander")
    refreshed = sm.resolve(sess.token)
    assert refreshed is not None
    pe.require(refreshed.role, "shift:close")  # now permitted
