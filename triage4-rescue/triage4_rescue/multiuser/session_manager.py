"""User + session stores + ``SessionManager``.

Both stores are in-memory by design. Sessions in a rescue ops centre
are short-lived (one shift, ~12 h) and tied to physical workstations
— there is no requirement to persist them. User profiles likewise sit
in memory; if a deployment needs durable user records they can be
restored on startup from a sibling system (LDAP, IdP) — this layer
does not assume that responsibility.

Token generation uses ``secrets.token_urlsafe`` so the value is
suitable for cookie / header use even though we never serialise it
across processes.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any

from .roles import ROLE_ORDER, RescueRole, validate_role


@dataclass(frozen=True)
class User:
    user_id: str
    role: RescueRole
    display_name: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Session:
    token: str
    user_id: str
    role: RescueRole
    payload: dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """In-memory user + session store with role-gated operations."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._sessions: dict[str, Session] = {}

    # -- user CRUD -----------------------------------------------------

    def create_user(
        self,
        user_id: str,
        role: str = "dispatcher",
        display_name: str = "",
        payload: dict[str, Any] | None = None,
    ) -> User:
        if not user_id:
            raise ValueError("user_id must not be empty")
        if user_id in self._users:
            raise ValueError(f"user {user_id!r} already exists")
        rescue_role = validate_role(role)
        user = User(
            user_id=user_id,
            role=rescue_role,
            display_name=display_name or user_id,
            payload=dict(payload or {}),
        )
        self._users[user_id] = user
        return user

    def get_user(self, user_id: str) -> User:
        if user_id not in self._users:
            raise KeyError(user_id)
        return self._users[user_id]

    def list_users(self) -> list[User]:
        return list(self._users.values())

    def update_role(self, user_id: str, new_role: str) -> User:
        existing = self.get_user(user_id)
        rescue_role = validate_role(new_role)
        updated = User(
            user_id=existing.user_id,
            role=rescue_role,
            display_name=existing.display_name,
            payload=dict(existing.payload),
        )
        self._users[user_id] = updated
        # Cascade role change into any open session.
        for token, sess in list(self._sessions.items()):
            if sess.user_id == user_id:
                self._sessions[token] = Session(
                    token=token,
                    user_id=user_id,
                    role=rescue_role,
                    payload=dict(sess.payload),
                )
        return updated

    def delete_user(self, user_id: str) -> None:
        if user_id not in self._users:
            raise KeyError(user_id)
        del self._users[user_id]
        # Drop any open sessions for the deleted user.
        for token in [t for t, s in self._sessions.items() if s.user_id == user_id]:
            del self._sessions[token]

    # -- session lifecycle --------------------------------------------

    def create_session(
        self,
        user_id: str,
        payload: dict[str, Any] | None = None,
    ) -> Session:
        user = self.get_user(user_id)
        token = secrets.token_urlsafe(24)
        sess = Session(
            token=token,
            user_id=user.user_id,
            role=user.role,
            payload=dict(payload or {}),
        )
        self._sessions[token] = sess
        return sess

    def resolve(self, token: str | None) -> Session | None:
        if not token:
            return None
        return self._sessions.get(token)

    def revoke(self, token: str) -> bool:
        return self._sessions.pop(token, None) is not None

    def require_role(self, token: str | None, minimum_role: str) -> Session:
        """Raise ``PermissionError`` unless the session's role rank
        meets or exceeds ``minimum_role``.
        """
        target = ROLE_ORDER[validate_role(minimum_role)]
        sess = self.resolve(token)
        if sess is None:
            raise PermissionError("missing or invalid session token")
        current = ROLE_ORDER[sess.role]
        if current < target:
            raise PermissionError(
                f"role {sess.role!r} insufficient; requires {minimum_role!r}"
            )
        return sess
