from __future__ import annotations

from dataclasses import dataclass, asdict

from triage4.core.models import CasualtySignature


@dataclass
class EvidenceToken:
    name: str
    strength: float
    source: str
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def build_evidence_tokens(sig: CasualtySignature) -> list[EvidenceToken]:
    tokens: list[EvidenceToken] = []

    if sig.bleeding_visual_score > 0.60:
        tokens.append(
            EvidenceToken(
                name="possible_external_bleeding",
                strength=sig.bleeding_visual_score,
                source="bleeding_signature",
                note="strong red/thermal pattern",
            )
        )

    if sig.chest_motion_fd < 0.18:
        tokens.append(
            EvidenceToken(
                name="low_chest_motion",
                strength=1.0 - sig.chest_motion_fd,
                source="breathing_signature",
                note="low chest motion complexity",
            )
        )

    if sig.perfusion_drop_score > 0.55:
        tokens.append(
            EvidenceToken(
                name="poor_perfusion_pattern",
                strength=sig.perfusion_drop_score,
                source="perfusion_signature",
                note="skin perfusion dropping",
            )
        )

    if sig.posture_instability_score > 0.60:
        tokens.append(
            EvidenceToken(
                name="abnormal_body_posture",
                strength=sig.posture_instability_score,
                source="posture_signature",
                note="posture collapse or instability",
            )
        )

    if sig.thermal_asymmetry_score > 0.60:
        tokens.append(
            EvidenceToken(
                name="thermal_anomaly",
                strength=sig.thermal_asymmetry_score,
                source="thermal_signature",
                note="local thermal asymmetry",
            )
        )

    return tokens
