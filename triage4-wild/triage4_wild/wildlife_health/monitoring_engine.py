"""WildlifeHealthEngine — the main reserve-pass engine.

Sibling of the prior monitoring engines. Takes one
``WildlifeObservation`` and produces one
``ReserveReport`` with a single per-animal
``WildlifeHealthScore`` + zero-or-more ``RangerAlert``
entries. Each alert is SMS-length-capped at construction
by the ``RangerAlert`` dataclass.

Observation-only, advisory-only, field-security-preserving.
See docs/PHILOSOPHY.md.
"""

from __future__ import annotations

from ..core.enums import (
    AlertKind,
    AlertLevel,
    CaptureQuality,
    MAX_RANGER_SMS_CHARS,
    ThreatKind,
)
from ..core.models import (
    RangerAlert,
    ReserveReport,
    ThreatConfidence,
    WildlifeHealthScore,
    WildlifeObservation,
)
from ..signatures.body_condition import compute_body_condition_safety
from ..signatures.postural_collapse import compute_postural_safety
from ..signatures.quadruped_gait import compute_gait_safety
from ..signatures.thermal_asymmetry import compute_thermal_safety
from .species_thresholds import profile_for


# Per-channel weights. Postural collapse is the highest-
# priority signal (a down-and-not-rising animal is the
# most urgent wildlife finding), followed by thermal (wound
# indicator), gait (lameness), body condition (slower-
# developing signal).
_CHANNEL_WEIGHTS: dict[str, float] = {
    "postural":        0.30,
    "thermal":         0.25,
    "gait":            0.25,
    "body_condition":  0.10,
    "threat_signal":   0.10,
}


# Per-channel alert thresholds — applied directly to the
# channel safety score.
_CHANNEL_URGENT: float = 0.40
_CHANNEL_WATCH: float = 0.65


# Capture-quality confidence scale. Night-IR captures
# produce reliable thermal readings but degraded pose;
# partial captures degrade everything.
_QUALITY_CONFIDENCE: dict[CaptureQuality, float] = {
    "good":     1.0,
    "partial":  0.6,
    "night_ir": 0.75,
}


class WildlifeHealthEngine:
    """Score one observation + emit SMS-length ranger alerts."""

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

    def review(
        self,
        observation: WildlifeObservation,
        reserve_id: str = "reserve",
    ) -> ReserveReport:
        prof = profile_for(observation.species)

        gait = compute_gait_safety(
            observation.pose_samples,
            observation.gait_samples,
        )
        thermal = compute_thermal_safety(observation.thermal_samples)
        postural = compute_postural_safety(observation.pose_samples)
        body_cond = compute_body_condition_safety(
            observation.body_condition_samples,
        )
        threat = self._threat_signal(observation.threat_signals)

        # Capture-quality blending on visible-light channels.
        conf = _QUALITY_CONFIDENCE[observation.capture_quality]
        gait_adj = gait * conf + 1.0 * (1.0 - conf)
        postural_adj = postural * conf + 1.0 * (1.0 - conf)
        body_cond_adj = body_cond * conf + 1.0 * (1.0 - conf)
        # Thermal stays intact — IR-based, condition-robust.

        overall = (
            self._weights["gait"] * gait_adj
            + self._weights["thermal"] * thermal
            + self._weights["postural"] * postural_adj
            + self._weights["body_condition"] * body_cond_adj
            + self._weights["threat_signal"] * threat
        )
        overall = max(0.0, min(1.0, overall))

        # High-value species escalation bias: if upstream
        # flagged a specific threat AND this is a high-value
        # species, tighten the alert thresholds.
        urgent_threshold = prof.overall_urgent_threshold
        watch_threshold = prof.overall_watch_threshold
        if prof.high_value_escalation and threat < 0.75:
            urgent_threshold = min(0.65, urgent_threshold + 0.10)
            watch_threshold = min(0.85, watch_threshold + 0.10)

        # Mortal-sign-style override: any channel in urgent
        # band forces overall level to urgent.
        channel_urgent = (
            gait < _CHANNEL_URGENT
            or thermal < _CHANNEL_URGENT
            or postural < _CHANNEL_URGENT
            or body_cond < _CHANNEL_URGENT
            or threat < _CHANNEL_URGENT
        )
        if channel_urgent:
            overall = min(overall, urgent_threshold - 0.01)

        if overall < urgent_threshold:
            alert_level: AlertLevel = "urgent"
        elif overall < watch_threshold:
            alert_level = "watch"
        else:
            alert_level = "ok"

        score = WildlifeHealthScore(
            obs_token=observation.obs_token,
            gait_safety=round(gait, 3),
            thermal_safety=round(thermal, 3),
            postural_safety=round(postural, 3),
            body_condition_safety=round(body_cond, 3),
            threat_signal=round(threat, 3),
            overall=round(overall, 3),
            alert_level=alert_level,
        )

        alerts = self._alerts_for(
            observation, score,
            gait=gait, thermal=thermal,
            postural=postural, body_cond=body_cond,
            threat=threat,
        )

        return ReserveReport(
            reserve_id=reserve_id,
            scores=[score],
            alerts=alerts,
        )

    # -- internals ------------------------------------------------------

    @staticmethod
    def _threat_signal(
        threats: list[ThreatConfidence],
    ) -> float:
        """Convert upstream threat-confidence entries into a
        unit-interval safety score. Any high-confidence
        threat flag drives safety toward 0."""
        if not threats:
            return 1.0
        max_conf = max(t.confidence for t in threats)
        return max(0.0, min(1.0, 1.0 - max_conf))

    def _alerts_for(
        self,
        obs: WildlifeObservation,
        score: WildlifeHealthScore,
        gait: float,
        thermal: float,
        postural: float,
        body_cond: float,
        threat: float,
    ) -> list[RangerAlert]:
        alerts: list[RangerAlert] = []
        loc = obs.location.handle
        spec = obs.species

        def _species_snippet() -> str:
            """Short species+handle header for alert body."""
            return f"{spec}, {loc}"

        channels: list[tuple[
            AlertKind, float, str, str,
        ]] = [
            ("gait", gait,
             "gait asymmetry / lameness pattern",
             "snare or impact injury, natural lameness, recent strain"),
            ("thermal", thermal,
             "focal thermal hotspot",
             "wound / inflammation, injury, thermal artefact"),
            ("collapse", postural,
             "sustained down-posture",
             "collapse, severe injury, ordinary rest at proximity"),
            ("body_condition", body_cond,
             "body condition low",
             "nutritional stress, chronic illness, lactation period"),
        ]

        for kind, value, desc, hint in channels:
            if value < _CHANNEL_URGENT:
                text = self._format_alert_text(
                    _species_snippet(), desc, hint, "urgent",
                )
                alerts.append(self._alert(
                    obs.obs_token, kind, "urgent", text, loc, value,
                ))
            elif value < _CHANNEL_WATCH:
                text = self._format_alert_text(
                    _species_snippet(), desc, hint, "watch",
                )
                alerts.append(self._alert(
                    obs.obs_token, kind, "watch", text, loc, value,
                ))

        # Threat-signal channel — fires only when an upstream
        # classifier attached a high-confidence threat.
        if threat < _CHANNEL_URGENT:
            # Pick the highest-confidence threat kind for
            # the alert text.
            top = max(
                obs.threat_signals,
                key=lambda t: t.confidence,
                default=None,
            )
            if top is not None:
                text = self._threat_alert_text(
                    _species_snippet(), top,
                )
                alerts.append(self._alert(
                    obs.obs_token, self._threat_kind_to_alert_kind(top.kind),
                    "urgent", text, loc, top.confidence,
                ))

        return alerts

    @staticmethod
    def _threat_kind_to_alert_kind(kind: ThreatKind) -> AlertKind:
        mapping: dict[ThreatKind, AlertKind] = {
            "snare_injury":       "gait",
            "thermal_asymmetry":  "thermal",
            "gait_instability":   "gait",
            "body_condition_low": "body_condition",
            "collapse":           "collapse",
        }
        return mapping[kind]

    @staticmethod
    def _format_alert_text(
        header: str,
        description: str,
        hint: str,
        tier: str,
    ) -> str:
        """Build a short, SMS-length ranger-alert body.

        Bodies are deliberately curt so the 200-char cap
        doesn't become a repeated source of alert rejections.
        """
        if tier == "urgent":
            core = (
                f"URGENT ({header}): {description}. "
                "Ranger + reserve vet review."
            )
        else:
            core = (
                f"WATCH ({header}): {description}. "
                "Ranger review next pass."
            )
        # Safety: truncate just in case, preserving the
        # field-security + SMS-length invariants. The
        # RangerAlert constructor still enforces the hard
        # cap.
        if len(core) > MAX_RANGER_SMS_CHARS:
            core = core[: MAX_RANGER_SMS_CHARS - 1] + "…"
        # Intentionally do NOT append `hint` to keep bodies
        # within the SMS cap; downstream consumer apps can
        # expand the short body into a longer report using
        # the alert's structured metadata.
        _ = hint
        return core

    @staticmethod
    def _threat_alert_text(
        header: str,
        top: ThreatConfidence,
    ) -> str:
        mapping: dict[ThreatKind, str] = {
            "snare_injury":       "possible snare-consistent pattern",
            "thermal_asymmetry":  "thermal asymmetry pattern",
            "gait_instability":   "marked gait instability",
            "body_condition_low": "low body condition pattern",
            "collapse":           "sustained down-posture",
        }
        core = (
            f"URGENT ({header}): {mapping[top.kind]}. "
            "Ranger + reserve vet review."
        )
        if len(core) > MAX_RANGER_SMS_CHARS:
            core = core[: MAX_RANGER_SMS_CHARS - 1] + "…"
        return core

    @staticmethod
    def _alert(
        obs_token: str,
        kind: AlertKind,
        level: AlertLevel,
        text: str,
        location_handle: str,
        observed_value: float,
    ) -> RangerAlert:
        return RangerAlert(
            obs_token=obs_token,
            kind=kind,
            level=level,
            text=text,
            location_handle=location_handle,
            observed_value=observed_value,
        )
