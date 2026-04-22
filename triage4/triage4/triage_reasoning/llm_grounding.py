"""LLM grounding layer — natural-language explanation for operators.

Part of Phase 9c (innovation pack 2, idea #12). The rule we follow is:

    **LLMs never make triage decisions. They only explain them.**

This module builds a structured prompt containing every numeric fact
triage4 has already decided — priority, contributions, uncertainty,
trauma hypotheses — and hands it off to any external LLM. The LLM's
job is to turn that structured evidence into a sentence or two in the
operator's language, never to introduce new clinical claims.

Default backend is ``TemplateGroundingBackend`` — an LLM-free template
renderer useful for unit tests, air-gapped demos, and as a stable
fallback when no LLM is available. A ``LLMBackend`` protocol is defined
so any provider (OpenAI, Anthropic, local ollama) can be plugged in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from triage4.core.models import CasualtyNode
from triage4.triage_reasoning.uncertainty import UncertaintyReport


@dataclass
class GroundingPrompt:
    system: str
    user: str
    facts: dict


@dataclass
class Explanation:
    casualty_id: str
    priority: str
    sentence: str
    facts: dict
    backend: str


class LLMBackend(Protocol):
    """Plug-in contract for any LLM provider."""

    name: str

    def complete(self, prompt: GroundingPrompt) -> str: ...


def build_prompt(
    node: CasualtyNode,
    triage_reasons: list[str],
    uncertainty: UncertaintyReport | None = None,
) -> GroundingPrompt:
    """Build a grounded prompt — no clinical claim is left for the LLM to invent."""
    sig = node.signatures

    facts: dict = {
        "casualty_id": node.id,
        "priority": node.triage_priority,
        "confidence": round(float(node.confidence), 3),
        "location": {"x": node.location.x, "y": node.location.y},
        "reasons": list(triage_reasons),
        "signatures": {
            "bleeding": round(sig.bleeding_visual_score, 3),
            "chest_motion_fd": round(sig.chest_motion_fd, 3),
            "perfusion_drop": round(sig.perfusion_drop_score, 3),
            "thermal_asymmetry": round(sig.thermal_asymmetry_score, 3),
            "posture_instability": round(sig.posture_instability_score, 3),
            "visibility": round(sig.visibility_score, 3),
        },
        "hypotheses": [
            {
                "kind": h.kind,
                "score": round(h.score, 3),
                "explanation": h.explanation,
            }
            for h in node.hypotheses
        ],
    }

    if uncertainty is not None:
        facts["overall_confidence"] = round(uncertainty.overall_confidence, 3)
        facts["overall_uncertainty"] = round(uncertainty.overall_uncertainty, 3)
        facts["per_channel_confidence"] = dict(uncertainty.per_channel_confidence)

    system = (
        "You are a triage briefing assistant. Explain the PROVIDED facts to a "
        "field medic in one or two concise sentences. Do NOT add any clinical "
        "claim that is not present in the facts. Use the exact priority label "
        "given. Keep numeric values consistent with the facts."
    )
    user = (
        "Explain this triage decision to the medic:\n"
        f"Casualty: {facts['casualty_id']}\n"
        f"Priority: {facts['priority']}\n"
        f"Confidence: {facts['confidence']}\n"
        f"Reasons: {', '.join(facts['reasons']) or '—'}\n"
        f"Hypotheses: {', '.join(h['kind'] for h in facts['hypotheses']) or '—'}"
    )

    return GroundingPrompt(system=system, user=user, facts=facts)


class TemplateGroundingBackend:
    """Deterministic LLM-free renderer — safe default."""

    name = "template"

    def complete(self, prompt: GroundingPrompt) -> str:
        f = prompt.facts
        reasons = f.get("reasons") or []
        hypotheses = f.get("hypotheses") or []

        if not reasons and not hypotheses:
            return (
                f"{f['casualty_id']}: priority {f['priority']}, "
                f"confidence {f['confidence']}."
            )

        reason_txt = "; ".join(reasons) if reasons else ""
        hyp_txt = (
            "hypotheses: " + ", ".join(h["kind"] for h in hypotheses)
            if hypotheses
            else ""
        )
        tail = " — ".join(s for s in (reason_txt, hyp_txt) if s)
        return (
            f"{f['casualty_id']}: priority {f['priority']} "
            f"(confidence {f['confidence']}). {tail}."
        ).strip()


def explain(
    node: CasualtyNode,
    triage_reasons: list[str],
    uncertainty: UncertaintyReport | None = None,
    backend: LLMBackend | None = None,
) -> Explanation:
    prompt = build_prompt(node, triage_reasons, uncertainty)
    backend = backend or TemplateGroundingBackend()
    sentence = backend.complete(prompt)
    return Explanation(
        casualty_id=node.id,
        priority=node.triage_priority,
        sentence=sentence,
        facts=prompt.facts,
        backend=backend.name,
    )
