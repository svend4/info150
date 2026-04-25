"""Role hierarchy for the rescue operations centre.

Four rescue-specific roles in strict ascending privilege order:

- ``viewer`` — read-only access to incidents and dashboards (e.g.
  outside observers, regulators, hospital liaisons).
- ``dispatcher`` — logs incidents, edits notes, assigns initial
  responders.
- ``incident_commander`` — closes shifts, dispatches resources across
  incidents, overrides dispatcher decisions.
- ``admin`` — manages users, edits the policy profile, configures the
  system. Operational privileges are a superset of incident_commander.

These names are deliberately divergent from v13's
``viewer/analyst/operator/admin`` SaaS template — see V13_REUSE_MAP.md
for the rationale.
"""

from __future__ import annotations

from typing import Literal

RescueRole = Literal["viewer", "dispatcher", "incident_commander", "admin"]

ROLE_ORDER: dict[RescueRole, int] = {
    "viewer": 0,
    "dispatcher": 1,
    "incident_commander": 2,
    "admin": 3,
}


def validate_role(role: str) -> RescueRole:
    """Return ``role`` typed as ``RescueRole`` if valid, else raise."""
    if role not in ROLE_ORDER:
        raise ValueError(
            f"unknown rescue role {role!r}; "
            f"valid: {sorted(ROLE_ORDER)}"
        )
    return role  # type: ignore[return-value]
