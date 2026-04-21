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


def main() -> None:
    triage_engine = RapidTriageEngine()
    graph = CasualtyGraph()
    polygonizer = BodyRegionPolygonizer()
    breath_extractor = BreathingSignatureExtractor()
    bleed_extractor = BleedingSignatureExtractor()
    perfusion_extractor = PerfusionSignatureExtractor()

    hints = [
        "immediate",
        "delayed",
        "minimal",
        "minimal",
        "delayed",
        "immediate",
        "minimal",
        "delayed",
    ]
    now = time.time()

    for idx, hint in enumerate(hints, start=1):
        x = round(random.uniform(8, 92), 1)
        y = round(random.uniform(8, 92), 1)

        body_regions = polygonizer.build_from_center(x, y)
        breathing = breath_extractor.extract(breath_signal(hint))
        vr, td, ph = bleeding_inputs(hint)
        bleeding = bleed_extractor.extract(vr, td, ph)
        perfusion = perfusion_extractor.extract(perfusion_series(hint))

        sig = CasualtySignature(
            breathing_curve=breathing["breathing_curve"],
            chest_motion_fd=breathing["chest_motion_fd"],
            perfusion_drop_score=perfusion["perfusion_drop_score"],
            bleeding_visual_score=bleeding["bleeding_visual_score"],
            visibility_score=1.0,
            body_region_polygons=body_regions,
            raw_features={
                "respiration_proxy": breathing["respiration_proxy"],
                "breathing_quality": breathing["quality_score"],
                "bleeding_confidence": bleeding["confidence"],
                "pulse_proxy": perfusion["pulse_proxy"],
            },
        )

        priority, conf, reasons = triage_engine.infer_priority(sig)
        hypotheses = triage_engine.build_hypotheses(sig)

        node = CasualtyNode(
            id=f"C{idx}",
            location=GeoPose(x=x, y=y),
            platform_source="sim_uav_1",
            confidence=round(max(conf, 0.50), 2),
            status="assessed",
            signatures=sig,
            hypotheses=hypotheses,
            triage_priority=priority,
            first_seen_ts=now,
            last_seen_ts=now,
        )

        graph.upsert(node)
        graph.link("sim_uav_1", "observed", node.id)

        print(node.id, priority, reasons)

    print("\nImmediate nodes:")
    for n in graph.immediate_nodes():
        print(n.id, n.triage_priority, n.confidence)


if __name__ == "__main__":
    main()
