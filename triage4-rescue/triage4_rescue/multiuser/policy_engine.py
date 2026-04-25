"""Role × action permission gate.

Composition rule: a role inherits **every** action granted to roles
below it in ``ROLE_ORDER``. So an ``incident_commander`` automatically
has all dispatcher + viewer actions; an ``admin`` has the full set.

The engine takes its grant table at construction time, so a deployment
can override the default vocabulary (e.g. give ``dispatcher`` the
``shift:close`` action if the local ops doctrine differs). Overrides
must use action strings that are valid ``RescueAction`` literals;
unknown actions raise ``ValueError`` immediately.
"""

from __future__ import annotations

from .actions import (
    DEFAULT_ROLE_ACTIONS,
    RescueAction,
    VALID_ACTIONS,
)
from .roles import ROLE_ORDER, RescueRole, validate_role


class PolicyEngine:
    def __init__(
        self,
        role_actions: dict[RescueRole, frozenset[RescueAction]] | None = None,
    ) -> None:
        grants = role_actions or DEFAULT_ROLE_ACTIONS
        # Validate that every supplied action is a known RescueAction.
        for role, actions in grants.items():
            validate_role(role)
            unknown = set(actions) - VALID_ACTIONS
            if unknown:
                raise ValueError(
                    f"unknown actions for role {role!r}: {sorted(unknown)}"
                )
        self._grants: dict[RescueRole, frozenset[RescueAction]] = dict(grants)

    def allowed_actions(self, role: str) -> frozenset[RescueAction]:
        rescue_role = validate_role(role)
        rank = ROLE_ORDER[rescue_role]
        out: set[RescueAction] = set()
        for r, level in ROLE_ORDER.items():
            if level <= rank:
                out.update(self._grants.get(r, frozenset()))
        return frozenset(out)

    def can(self, role: str, action: str) -> bool:
        if action not in VALID_ACTIONS:
            return False
        return action in self.allowed_actions(role)  # type: ignore[operator]

    def require(self, role: str, action: str) -> None:
        if not self.can(role, action):
            raise PermissionError(
                f"role {role!r} cannot perform {action!r}"
            )
