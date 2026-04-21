from pathlib import Path

from triage4.core.models import CasualtyNode, CasualtySignature, GeoPose, TraumaHypothesis
from triage4.graph.casualty_graph import CasualtyGraph
from triage4.ui.html_export import render_html


def _graph_with(casualties: list[tuple[str, str, float, float]]) -> CasualtyGraph:
    g = CasualtyGraph()
    for cid, priority, x, y in casualties:
        g.upsert(
            CasualtyNode(
                id=cid,
                location=GeoPose(x=x, y=y),
                platform_source="uav",
                confidence=0.85,
                status="assessed",
                signatures=CasualtySignature(),
                hypotheses=[TraumaHypothesis(kind="hemorrhage", score=0.9)],
                triage_priority=priority,
            )
        )
        g.link("uav", "observed", cid)
    return g


def test_render_html_writes_self_contained_file(tmp_path: Path):
    graph = _graph_with([("C1", "immediate", 10.0, 20.0), ("C2", "minimal", 60.0, 60.0)])
    out = render_html(graph, out_path=tmp_path / "export.html", timestamp="2026-04-21")
    path = Path(out)

    assert path.exists()
    html_body = path.read_text(encoding="utf-8")

    # Must be a standalone document.
    assert "<!doctype html>" in html_body.lower()
    # Casualty ids must appear in the embedded JSON.
    assert "C1" in html_body and "C2" in html_body
    # Palette colors for priorities must appear.
    assert "#ff5c5c" in html_body
    assert "#63d471" in html_body
    # Timestamp rendered verbatim.
    assert "2026-04-21" in html_body
    # No external CDN dependency (offline-safe). We allow the SVG namespace
    # URI since it's just an XML identifier, not a network fetch.
    lowered = html_body.lower()
    assert "cdn.jsdelivr.net" not in lowered
    assert "unpkg.com" not in lowered
    assert "cdnjs.cloudflare.com" not in lowered
    assert "d3js.org" not in lowered


def test_render_html_empty_graph(tmp_path: Path):
    out = render_html(CasualtyGraph(), out_path=tmp_path / "empty.html")
    path = Path(out)
    assert path.exists()
    body = path.read_text(encoding="utf-8")
    assert "0 casualties" in body
