from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class GeoPose:
    x: float
    y: float
    z: float = 0.0
    yaw: float = 0.0
    frame: str = "map"


@dataclass
class TraumaHypothesis:
    kind: str
    score: float
    evidence: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class CasualtySignature:
    breathing_curve: list[float] = field(default_factory=list)
    chest_motion_fd: float = 0.0
    perfusion_drop_score: float = 0.0
    thermal_asymmetry_score: float = 0.0
    bleeding_visual_score: float = 0.0
    posture_instability_score: float = 0.0
    visibility_score: float = 1.0
    body_region_polygons: dict[str, list[tuple[float, float]]] = field(default_factory=dict)
    raw_features: dict[str, Any] = field(default_factory=dict)


@dataclass
class CasualtyNode:
    id: str
    location: GeoPose
    platform_source: str
    confidence: float
    status: str
    signatures: CasualtySignature = field(default_factory=CasualtySignature)
    hypotheses: list[TraumaHypothesis] = field(default_factory=list)
    triage_priority: str = "unknown"
    first_seen_ts: float = 0.0
    last_seen_ts: float = 0.0
    assigned_medic: str | None = None
    assigned_robot: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
