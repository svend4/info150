"""PetTriageEngine — dual-audience pre-visit assessment engine.

Takes one ``PetObservation`` and produces one ``PetReport``
containing:
- a ``PetAssessment`` (per-channel scores + triage recommendation)
- a ``VetSummary`` (vet-facing, permissive on clinical vocab)
- zero-or-more ``OwnerMessage`` entries (owner-facing,
  strict layperson guard)

Observation-only. Never a definitive diagnosis. Owner text
never carries reassurance that would let the owner skip a
vet visit. Vet text never carries operational scheduling.
See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from ..core.enums import SpeciesKind, TriageRecommendation, VideoQuality
from ..core.models import (
    OwnerMessage,
    PetAssessment,
    PetObservation,
    PetReport,
    VetSummary,
)
from ..signatures.cardiac_band import compute_cardiac_safety
from ..signatures.gait_asymmetry import compute_gait_safety
from ..signatures.pain_behaviors import compute_pain_safety
from ..signatures.respiratory_distress import compute_respiratory_safety
from .species_profiles import profile_for


# Per-channel weights for the overall score fusion. Pain
# behaviors weighted highest because they capture the
# species-specific wisdom most vets consult first. Gait is
# second because lameness is the most common owner-uploaded
# concern. Respiratory and cardiac follow.
_CHANNEL_WEIGHTS: dict[str, float] = {
    "pain":        0.35,
    "gait":        0.30,
    "respiratory": 0.20,
    "cardiac":     0.15,
}


# Video-quality confidence scale. Shaky / occluded / low-
# light clips blend the gait + pain signals toward neutral —
# the library can't see clearly enough to call those
# channels confidently. Respiratory + cardiac come from
# more robust signals and stay intact.
_QUALITY_CONFIDENCE: dict[VideoQuality, float] = {
    "good":      1.0,
    "shaky":     0.8,
    "low_light": 0.7,
    "occluded":  0.5,
}


class PetTriageEngine:
    """Produce a dual-audience pre-visit report from one observation."""

    def __init__(
        self,
        weights: dict[str, float] | None = None,
    ) -> None:
        w = dict(weights or _CHANNEL_WEIGHTS)
        total = sum(w.values())
        if total <= 0:
            raise ValueError("weight total must be positive")
        self._weights = {k: v / total for k, v in w.items()}

    # -- public API -----------------------------------------------------

    def review(self, obs: PetObservation) -> PetReport:
        prof = profile_for(obs.species)

        gait = compute_gait_safety(obs.gait_samples)
        respiratory = compute_respiratory_safety(
            obs.breathing_samples, obs.species,
        )
        cardiac = compute_cardiac_safety(obs.hr_samples, obs.species)
        pain = compute_pain_safety(obs.pain_samples, obs.species)

        conf = _QUALITY_CONFIDENCE[obs.video_quality]
        gait_adj = gait * conf + 1.0 * (1.0 - conf)
        pain_adj = pain * conf + 1.0 * (1.0 - conf)

        overall = (
            self._weights["pain"] * pain_adj
            + self._weights["gait"] * gait_adj
            + self._weights["respiratory"] * respiratory
            + self._weights["cardiac"] * cardiac
        )
        overall = max(0.0, min(1.0, overall))

        # Recommendation — per-species thresholds.
        if overall < prof.see_today_threshold:
            recommendation: TriageRecommendation = "see_today"
        elif overall < prof.routine_visit_threshold:
            recommendation = "routine_visit"
        else:
            recommendation = "can_wait"

        assessment = PetAssessment(
            pet_token=obs.pet_token,
            gait_safety=round(gait, 3),
            respiratory_safety=round(respiratory, 3),
            cardiac_safety=round(cardiac, 3),
            pain_safety=round(pain, 3),
            overall=round(overall, 3),
            recommendation=recommendation,
        )

        vet_summary = self._build_vet_summary(
            obs, assessment, gait, respiratory, cardiac, pain,
        )
        owner_messages = self._build_owner_messages(
            obs, assessment, gait, respiratory, cardiac, pain,
        )

        return PetReport(
            pet_token=obs.pet_token,
            assessment=assessment,
            vet_summary=vet_summary,
            owner_messages=owner_messages,
        )

    # -- internals ------------------------------------------------------

    def _build_vet_summary(
        self,
        obs: PetObservation,
        assessment: PetAssessment,
        gait: float,
        respiratory: float,
        cardiac: float,
        pain: float,
    ) -> VetSummary:
        """Grounded multi-paragraph summary for the vet.

        Permissive on clinical vocabulary; refuses
        definitive diagnosis + operational scheduling.
        """
        age_str = (
            f"est. {obs.age_years:.1f} yr"
            if obs.age_years is not None
            else "age not supplied"
        )
        lines: list[str] = []
        lines.append(
            f"Species: {obs.species}. {age_str}. "
            f"Clip: {obs.window_duration_s:.0f} s · "
            f"video quality: {obs.video_quality}."
        )

        # Per-channel grounded observations.
        gait_text = self._vet_gait_line(gait, obs.gait_samples)
        resp_text = self._vet_respiratory_line(
            respiratory, obs.breathing_samples, obs.species,
        )
        card_text = self._vet_cardiac_line(
            cardiac, obs.hr_samples, obs.species,
        )
        pain_text = self._vet_pain_line(pain, obs.pain_samples)
        lines.extend([gait_text, resp_text, card_text, pain_text])

        lines.append(
            f"Pre-visit recommendation: {assessment.recommendation}."
        )
        return VetSummary(
            pet_token=obs.pet_token,
            text=" ".join(lines),
        )

    @staticmethod
    def _vet_gait_line(gait: float, samples: list) -> str:
        if not samples:
            return "Gait: no observations (pet was still throughout clip)."
        if gait >= 0.9:
            return "Gait: symmetric, rhythmic across the observed cycles."
        if gait >= 0.6:
            return (
                f"Gait: mild asymmetry observed (safety {gait:.2f}). "
                "Possible compensating pattern; worth a closer look "
                "in-exam."
            )
        return (
            f"Gait: pronounced asymmetry across the clip "
            f"(safety {gait:.2f}). Suggestive of forelimb or "
            "hindlimb lameness; grade + side best determined in "
            "exam."
        )

    @staticmethod
    def _vet_respiratory_line(
        respiratory: float, samples: list, species: SpeciesKind,
    ) -> str:
        if not samples:
            return "Respiratory: no reliable rate samples in clip."
        median = sorted(s.rate_bpm for s in samples)[len(samples) // 2]
        at_rest_high = any(s.at_rest and s.rate_bpm > 30 for s in samples)
        tag = ""
        if at_rest_high:
            tag = "; panting-at-rest observed"
        return (
            f"Respiratory: median rate {median:.0f} bpm "
            f"(species reference varies{tag}), "
            f"channel safety {respiratory:.2f}."
        )

    @staticmethod
    def _vet_cardiac_line(
        cardiac: float, samples: list, species: SpeciesKind,
    ) -> str:
        reliable = [s for s in samples if s.reliable]
        if not reliable:
            return (
                "Cardiac: HR estimate unreliable in this clip (pet "
                "not still enough / lighting poor)."
            )
        median = sorted(s.hr_bpm for s in reliable)[len(reliable) // 2]
        return (
            f"Cardiac: median HR {median:.0f} bpm (reliable samples), "
            f"channel safety {cardiac:.2f}."
        )

    @staticmethod
    def _vet_pain_line(pain: float, samples: list) -> str:
        if not samples:
            return "Pain behaviours: none classified in clip."
        behaviors = sorted({s.kind for s in samples})
        behaviors_str = ", ".join(behaviors)
        return (
            f"Pain behaviours: observed ({behaviors_str}); "
            f"channel safety {pain:.2f}."
        )

    def _build_owner_messages(
        self,
        obs: PetObservation,
        assessment: PetAssessment,
        gait: float,
        respiratory: float,
        cardiac: float,
        pain: float,
    ) -> list[OwnerMessage]:
        """Owner-friendly messages.

        Strict claims guard — layperson language only, never
        reassurance, always pointing toward vet consultation.
        """
        messages: list[OwnerMessage] = []
        tok = obs.pet_token

        # Headline message anchored on the recommendation.
        if assessment.recommendation == "see_today":
            headline = (
                f"Your {obs.species}'s clip shows patterns that "
                "warrant a same-day look by your vet. Please "
                "contact them today."
            )
        elif assessment.recommendation == "routine_visit":
            headline = (
                f"Your {obs.species}'s clip shows a few things "
                "that your vet should review. Please share this "
                "with them and consider scheduling a visit."
            )
        else:
            # can_wait — still friendly, never reassuring.
            # Deliberately worded to send the owner toward
            # the vet at their next routine appointment.
            headline = (
                f"Your {obs.species}'s clip did not show strong "
                "concern signals in this 60-second window. "
                "Share this clip with your vet at the next "
                "routine visit so they have a baseline."
            )
        messages.append(OwnerMessage(pet_token=tok, text=headline))

        # Channel-specific follow-ups when a channel is in
        # the lower safety band. Kept short, layperson
        # vocabulary only.
        if gait < 0.7:
            messages.append(OwnerMessage(
                pet_token=tok,
                text=(
                    f"Your {obs.species} is moving unevenly in "
                    "the clip. Your vet may want to watch them "
                    "walk in person."
                ),
            ))
        if respiratory < 0.7:
            messages.append(OwnerMessage(
                pet_token=tok,
                text=(
                    f"Your {obs.species}'s breathing pattern "
                    "looked faster than typical. Worth sharing "
                    "this clip with your vet."
                ),
            ))
        if pain < 0.7:
            messages.append(OwnerMessage(
                pet_token=tok,
                text=(
                    f"Your {obs.species} showed behaviour in the "
                    "clip that pet-care guides associate with "
                    "discomfort. Your vet can help figure out "
                    "what's going on."
                ),
            ))
        return messages
