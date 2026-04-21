"""Self-contained HTML export of a CasualtyGraph.

Pattern borrowed from svend4/infom ``visualizer/html.py`` — one function
that serialises the domain graph into JSON and embeds it in a D3.js
template so the result is a single HTML file that works offline.

The infom upstream targets a rich ``KnowledgeMap`` (communities, hex
signatures, heptagrams, fractal borders). triage4 only needs a tactical
casualty-graph view, so this implementation is fully written from scratch
against the triage4 data model — only the overall pattern is reused.

Output contract:
    render_html(graph, out_path) -> str: path to the written HTML
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from triage4.graph.casualty_graph import CasualtyGraph


_PRIORITY_COLOR: dict[str, str] = {
    "immediate": "#ff5c5c",
    "delayed": "#ffb84d",
    "minimal": "#63d471",
    "expectant": "#7a8ba6",
    "unknown": "#a0aec0",
}


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>triage4 — casualty graph</title>
<style>
  :root {{ color-scheme: dark; }}
  html, body {{ margin:0; height:100%; background:#0b1020; color:#e5ecff;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  #root {{ display:grid; grid-template-columns: 300px 1fr; height:100vh; }}
  aside {{ padding:16px; border-right:1px solid #1e2a44; overflow-y:auto; }}
  h1 {{ font-size:18px; margin:0 0 12px 0; }}
  svg {{ width:100%; height:100%; display:block; background:#070714; }}
  .card {{ background:#0e1528; border-radius:10px; padding:10px 12px; margin-bottom:10px;
    border:1px solid #1e2a44; }}
  .pill {{ display:inline-block; padding:2px 8px; border-radius:999px;
    font-size:11px; text-transform:uppercase; letter-spacing:1px; }}
  .small {{ font-size:11px; opacity:.7; }}
</style>
</head>
<body>
<div id="root">
  <aside>
    <h1>triage4</h1>
    <div class="small">exported {timestamp}</div>
    <div class="small">{n_nodes} casualties · {n_edges} edges</div>
    <hr style="opacity:.2;margin:14px 0" />
    <div id="cards"></div>
  </aside>
  <svg id="scene" viewBox="0 0 800 800"></svg>
</div>
<script>
const DATA = {payload};

const svg = document.getElementById('scene');
const cards = document.getElementById('cards');
const W = 800, H = 800;

function scale(v) {{ return 40 + v * 7; }}
function color(p) {{ return DATA.palette[p] || DATA.palette.unknown; }}

for (const [a, rel, b] of DATA.edges) {{
  const na = DATA.nodes.find(n => n.id === a);
  const nb = DATA.nodes.find(n => n.id === b);
  if (!na || !nb) continue;
  const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  line.setAttribute('x1', scale(na.x)); line.setAttribute('y1', scale(na.y));
  line.setAttribute('x2', scale(nb.x)); line.setAttribute('y2', scale(nb.y));
  line.setAttribute('stroke', '#30405f'); line.setAttribute('stroke-width', '1');
  svg.appendChild(line);
}}

for (const n of DATA.nodes) {{
  const c = color(n.priority);
  const halo = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  halo.setAttribute('cx', scale(n.x)); halo.setAttribute('cy', scale(n.y));
  halo.setAttribute('r', 16); halo.setAttribute('fill', c);
  halo.setAttribute('opacity', '0.18');
  svg.appendChild(halo);

  const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  dot.setAttribute('cx', scale(n.x)); dot.setAttribute('cy', scale(n.y));
  dot.setAttribute('r', 6); dot.setAttribute('fill', c);
  svg.appendChild(dot);

  const txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  txt.setAttribute('x', scale(n.x) + 10); txt.setAttribute('y', scale(n.y) - 8);
  txt.setAttribute('fill', '#e5ecff'); txt.setAttribute('font-size', '12');
  txt.textContent = n.id;
  svg.appendChild(txt);

  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = `
    <div style="font-weight:700">${{n.id}}</div>
    <div><span class="pill" style="background:${{c}}22;color:${{c}};border:1px solid ${{c}}66">${{n.priority}}</span></div>
    <div class="small">confidence: ${{n.confidence.toFixed(2)}}</div>
    <div class="small">platform: ${{n.platform || '—'}}</div>
  `;
  cards.appendChild(card);
}}
</script>
</body>
</html>
"""


def _graph_payload(graph: CasualtyGraph) -> dict:
    nodes = [
        {
            "id": n.id,
            "x": float(n.location.x),
            "y": float(n.location.y),
            "priority": n.triage_priority,
            "confidence": float(n.confidence),
            "platform": n.platform_source,
        }
        for n in graph.all_nodes()
    ]
    edges = [list(e) for e in graph.edges]
    return {"nodes": nodes, "edges": edges, "palette": dict(_PRIORITY_COLOR)}


def render_html(
    graph: CasualtyGraph,
    out_path: str | Path = "triage4_casualties.html",
    timestamp: str = "",
) -> str:
    """Render a self-contained HTML file for a CasualtyGraph.

    Returns the written path as a string.
    """
    payload = _graph_payload(graph)
    payload_json = json.dumps(payload, ensure_ascii=False)

    body = _HTML_TEMPLATE.format(
        payload=payload_json,
        timestamp=html.escape(timestamp or "now"),
        n_nodes=len(payload["nodes"]),
        n_edges=len(payload["edges"]),
    )

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    return str(out)
