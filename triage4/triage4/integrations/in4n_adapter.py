"""Scene export compatible with in4n-style force-graph viewers.

Adapted from the `in4n` project's force-graph layout (`react-force-graph` +
`three.js`). triage4 only needs the export contract: a JSON payload with
`nodes` (id, group, val, x, y, label, color) and `links` (source, target,
kind, strength). Actual rendering stays on the React side.

See `third_party/IN4N_ATTRIBUTION.md` for provenance.
"""

from __future__ import annotations

from triage4.graph.casualty_graph import CasualtyGraph


_PRIORITY_COLOR: dict[str, str] = {
    "immediate": "#ff5c5c",
    "delayed": "#ffb84d",
    "minimal": "#63d471",
    "expectant": "#7a8ba6",
    "unknown": "#a0aec0",
}

_LINK_STRENGTH: dict[str, float] = {
    "observed": 0.8,
    "located_in": 0.4,
    "caused": 0.7,
    "supports": 0.6,
}


class In4nSceneAdapter:
    """Builds a force-graph scene description from a CasualtyGraph.

    Output format matches the node/link contract expected by
    `react-force-graph` (2D or 3D).
    """

    def export_scene(
        self,
        graph: CasualtyGraph,
        platforms: list[dict] | None = None,
    ) -> dict:
        nodes = [
            {
                "id": n.id,
                "label": n.id,
                "group": n.triage_priority,
                "val": max(2.0, 12.0 * n.confidence),
                "color": _PRIORITY_COLOR.get(n.triage_priority, "#a0aec0"),
                "x": n.location.x,
                "y": n.location.y,
                "z": n.location.z,
                "kind": "casualty",
                "confidence": n.confidence,
            }
            for n in graph.all_nodes()
        ]

        for p in platforms or []:
            nodes.append(
                {
                    "id": p.get("id"),
                    "label": p.get("id"),
                    "group": "platform",
                    "val": 6.0,
                    "color": "#4fc3f7",
                    "x": float(p.get("x", 0.0)),
                    "y": float(p.get("y", 0.0)),
                    "z": float(p.get("z", 0.0)),
                    "kind": p.get("kind", "platform"),
                }
            )

        links = [
            {
                "source": src,
                "target": dst,
                "kind": rel,
                "strength": _LINK_STRENGTH.get(rel, 0.5),
            }
            for (src, rel, dst) in graph.edges
        ]
        return {"nodes": nodes, "links": links}
