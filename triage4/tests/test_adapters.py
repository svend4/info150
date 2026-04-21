from triage4.core.models import CasualtyNode, GeoPose
from triage4.graph.casualty_graph import CasualtyGraph
from triage4.integrations.in4n_adapter import In4nSceneAdapter
from triage4.integrations.infom_adapter import InfoMGraphAdapter
from triage4.integrations.meta2_adapter import Meta2SignatureAdapter


def _graph_with(cid: str, priority: str) -> CasualtyGraph:
    g = CasualtyGraph()
    g.upsert(
        CasualtyNode(
            id=cid,
            location=GeoPose(x=10.0, y=20.0),
            platform_source="uav",
            confidence=0.9,
            status="assessed",
            triage_priority=priority,
        )
    )
    g.link("uav", "observed", cid)
    return g


def test_meta2_adapter_delegates_to_fractal_math():
    adapter = Meta2SignatureAdapter()
    jagged = [0.1, 0.9, 0.1, 0.9, 0.1, 0.9, 0.1, 0.9]
    v = adapter.to_fractal_motion(jagged)
    assert 0.0 <= v <= 1.0


def test_infom_adapter_produces_versioned_snapshot():
    adapter = InfoMGraphAdapter()
    adapter.record_assessment("C1", "immediate", 0.88)
    snap = adapter.snapshot(_graph_with("C1", "immediate"), name="t0")

    assert snap["version"] == 2
    assert snap["snapshot_name"] == "t0"
    assert "evidence_memory" in snap
    assert "casualty_graph" in snap


def test_in4n_adapter_emits_force_graph_shape():
    adapter = In4nSceneAdapter()
    scene = adapter.export_scene(
        _graph_with("C1", "immediate"),
        platforms=[{"id": "uav_1", "x": 5.0, "y": 5.0, "kind": "uav"}],
    )

    node_ids = {n["id"] for n in scene["nodes"]}
    assert {"C1", "uav_1"} <= node_ids

    casualty = next(n for n in scene["nodes"] if n["id"] == "C1")
    assert casualty["group"] == "immediate"
    assert casualty["color"] == "#ff5c5c"
    assert casualty["val"] > 0

    assert scene["links"]
    assert all("strength" in link for link in scene["links"])
