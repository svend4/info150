from __future__ import annotations

import random
import time

from triage4.core.models import CasualtyNode, CasualtySignature, GeoPose
from triage4.graph.casualty_graph import CasualtyGraph
from triage4.perception.body_regions import BodyRegionPolygonizer
from triage4.signatures.bleeding_signature import BleedingSignatureExtractor
from triage4.signatures.breathing_signature import BreathingSignatureExtractor
from triage4.signatures.perfusion_signature import PerfusionSignatureExtractor
from triage4.sim.casualty_profiles import breath_signal, bleeding_inputs, perfusion_series
from triage4.triage_reasoning.rapid_triage import RapidTriageEngine


DEMO_ROWS: list[tuple[str, str, float, float]] = [
    ("C1", "immediate", 18.0, 24.0),
    ("C2", "delayed", 36.0, 42.0),
    ("C3", "minimal", 61.0, 28.0),
    ("C4", "delayed", 74.0, 61.0),
    ("C5", "immediate", 48.0, 77.0),
]


def seed_demo_data(
    graph: CasualtyGraph,
    triage_engine: RapidTriageEngine | None = None,
    polygonizer: BodyRegionPolygonizer | None = None,
    breath_extractor: BreathingSignatureExtractor | None = None,
    bleed_extractor: BleedingSignatureExtractor | None = None,
    perfusion_extractor: PerfusionSignatureExtractor | None = None,
    rng: random.Random | None = None,
) -> None:
    if graph.nodes:
        return

    triage_engine = triage_engine or RapidTriageEngine()
    polygonizer = polygonizer or BodyRegionPolygonizer()
    breath_extractor = breath_extractor or BreathingSignatureExtractor()
    bleed_extractor = bleed_extractor or BleedingSignatureExtractor()
    perfusion_extractor = perfusion_extractor or PerfusionSignatureExtractor()
    rng = rng or random.Random()

    now = time.time()

    for cid, priority_hint, x, y in DEMO_ROWS:
        breathing = breath_extractor.extract(breath_signal(priority_hint))
        vr, td, ph = bleeding_inputs(priority_hint)
        bleeding = bleed_extractor.extract(vr, td, ph)
        perfusion = perfusion_extractor.extract(perfusion_series(priority_hint))
        body_regions = polygonizer.build_from_center(x, y)

        sig = CasualtySignature(
            breathing_curve=breathing["breathing_curve"],
            chest_motion_fd=breathing["chest_motion_fd"],
            perfusion_drop_score=perfusion["perfusion_drop_score"],
            bleeding_visual_score=bleeding["bleeding_visual_score"],
            visibility_score=round(rng.uniform(0.78, 1.0), 2),
            body_region_polygons=body_regions,
            raw_features={
                "respiration_proxy": breathing["respiration_proxy"],
                "breathing_quality": breathing["quality_score"],
                "bleeding_confidence": bleeding["confidence"],
                "pulse_proxy": perfusion["pulse_proxy"],
            },
        )

        priority, conf, _ = triage_engine.infer_priority(sig)
        node = CasualtyNode(
            id=cid,
            location=GeoPose(x=x, y=y),
            platform_source="demo_uav",
            confidence=round(max(conf, 0.50), 2),
            status="assessed",
            signatures=sig,
            hypotheses=triage_engine.build_hypotheses(sig),
            triage_priority=priority,
            first_seen_ts=now,
            last_seen_ts=now,
        )
        graph.upsert(node)
        graph.link("demo_uav", "observed", cid)
