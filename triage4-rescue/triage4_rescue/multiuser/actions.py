"""Action vocabulary for the rescue operations centre.

Action names use the ``<resource>:<verb>`` convention from v13. The
vocabulary is rescue-specific: incidents, responders, resources,
shifts, users, policy. There is **no** scenario / workspace / casualty
vocabulary because rescue's source-of-truth dataclasses are
``IncidentReport``, not v13's ``Scenario`` or ``Casualty``.

Each role inherits all actions from lower roles via ``PolicyEngine``.
This file lists only the actions a role gains when it crosses into
that level.
"""

from __future__ import annotations

from typing import Literal

from .roles import RescueRole

RescueAction = Literal[
    # viewer
    "incident:read",
    "responder:read",
    "shift:read",
    "audit:read_basic",
    # dispatcher
    "incident:log",
    "incident:annotate",
    "responder:assign",
    "audit:read",
    # incident_commander
    "incident:close",
    "resource:dispatch",
    "shift:close",
    "responder:reassign",
    # admin
    "users:mutate",
    "users:delete",
    "policy:read",
    "policy:mutate",
]

VALID_ACTIONS: frozenset[RescueAction] = frozenset(
    [
        "incident:read",
        "responder:read",
        "shift:read",
        "audit:read_basic",
        "incident:log",
        "incident:annotate",
        "responder:assign",
        "audit:read",
        "incident:close",
        "resource:dispatch",
        "shift:close",
        "responder:reassign",
        "users:mutate",
        "users:delete",
        "policy:read",
        "policy:mutate",
    ]
)


# Per-role action grants. Lower roles do NOT include their grant; the
# PolicyEngine composes inherited grants by walking ROLE_ORDER.
DEFAULT_ROLE_ACTIONS: dict[RescueRole, frozenset[RescueAction]] = {
    "viewer": frozenset(
        ["incident:read", "responder:read", "shift:read", "audit:read_basic"]
    ),
    "dispatcher": frozenset(
        [
            "incident:log",
            "incident:annotate",
            "responder:assign",
            "audit:read",
        ]
    ),
    "incident_commander": frozenset(
        [
            "incident:close",
            "resource:dispatch",
            "shift:close",
            "responder:reassign",
        ]
    ),
    "admin": frozenset(
        [
            "users:mutate",
            "users:delete",
            "policy:read",
            "policy:mutate",
        ]
    ),
}
