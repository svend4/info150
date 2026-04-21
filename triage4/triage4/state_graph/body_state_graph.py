from __future__ import annotations

from triage4.semantic.evidence_tokens import EvidenceToken


_SUPPORTS: dict[str, list[str]] = {
    "possible_external_bleeding": ["hemorrhage_risk"],
    "low_chest_motion": ["respiratory_distress", "unresponsive"],
    "poor_perfusion_pattern": ["shock_risk", "hemorrhage_risk"],
    "abnormal_body_posture": ["unresponsive", "severe_trauma_suspicion"],
    "thermal_anomaly": ["hemorrhage_risk", "severe_trauma_suspicion"],
}


class BodyStateGraph:
    """Simple hypothesis graph aggregated from evidence tokens."""

    def __init__(self) -> None:
        self.nodes: set[str] = set()
        self.edges: list[tuple[str, str, str]] = []
        self.hypothesis_scores: dict[str, float] = {}

    def ingest(self, tokens: list[EvidenceToken]) -> None:
        for token in tokens:
            self.nodes.add(token.name)
            for hypothesis in _SUPPORTS.get(token.name, []):
                self.nodes.add(hypothesis)
                self.edges.append((token.name, "supports", hypothesis))
                self.hypothesis_scores[hypothesis] = round(
                    max(self.hypothesis_scores.get(hypothesis, 0.0), token.strength),
                    3,
                )

    def ranked_hypotheses(self) -> list[tuple[str, float]]:
        return sorted(self.hypothesis_scores.items(), key=lambda kv: kv[1], reverse=True)

    def as_json(self) -> dict:
        return {
            "nodes": sorted(self.nodes),
            "edges": self.edges,
            "hypothesis_scores": dict(self.hypothesis_scores),
        }
