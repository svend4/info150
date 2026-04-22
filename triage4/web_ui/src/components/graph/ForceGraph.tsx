// Tiny force-directed layout. No external deps — stdlib math.
// Enough for ≤100 nodes; for larger graphs we'd swap to d3-force or
// react-force-graph, but the triage4 casualty graph is always small.

import { useEffect, useMemo, useRef, useState } from "react";

import type { GraphData } from "../../types";
import { priorityColor } from "../../util/priority";

type Point = { x: number; y: number; vx: number; vy: number };

const ITERATIONS = 250;
const REPEL = 8000;
const SPRING = 0.01;
const DAMPING = 0.85;
const REST_LENGTH = 100;

type Props = {
  data: GraphData;
  width?: number;
  height?: number;
};

export default function ForceGraph({
  data,
  width = 720,
  height = 480,
}: Props) {
  const [hover, setHover] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  const positions = useMemo(() => {
    return layout(data, width, height);
  }, [data, width, height]);

  useEffect(() => {
    // Reset hover when the dataset changes.
    setHover(null);
  }, [data]);

  if (data.nodes.length === 0) {
    return (
      <div
        style={{
          padding: 24,
          color: "var(--text-2)",
          fontStyle: "italic",
          textAlign: "center",
        }}
      >
        graph has no nodes
      </div>
    );
  }

  return (
    <div ref={canvasRef}>
      <svg
        width={width}
        height={height}
        style={{
          border: "1px solid var(--border-1)",
          borderRadius: "var(--r2)",
          background: "var(--bg-1)",
        }}
      >
        {data.edges.map(([src, , dst], idx) => {
          const a = positions.get(src);
          const b = positions.get(dst);
          if (!a || !b) return null;
          return (
            <line
              key={idx}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="var(--border-2)"
              strokeWidth={1}
              opacity={hover && hover !== src && hover !== dst ? 0.2 : 0.7}
            />
          );
        })}

        {data.nodes.map((node) => {
          const pos = positions.get(node.id);
          if (!pos) return null;
          const highlighted = hover === node.id;
          return (
            <g
              key={node.id}
              onMouseEnter={() => setHover(node.id)}
              onMouseLeave={() => setHover(null)}
              style={{ cursor: "pointer" }}
            >
              <circle
                cx={pos.x}
                cy={pos.y}
                r={highlighted ? 14 : 10}
                fill={priorityColor(node.triage_priority)}
                stroke={highlighted ? "var(--accent)" : "var(--border-2)"}
                strokeWidth={highlighted ? 2 : 1}
              />
              <text
                x={pos.x}
                y={pos.y - 16}
                textAnchor="middle"
                fill="var(--text-0)"
                style={{
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  opacity: highlighted ? 1 : 0.75,
                }}
              >
                {node.id}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function layout(
  data: GraphData,
  width: number,
  height: number,
): Map<string, Point> {
  const positions = new Map<string, Point>();
  const ids = data.nodes.map((n) => n.id);

  // Initial circular layout.
  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) * 0.35;
  ids.forEach((id, idx) => {
    const angle = (2 * Math.PI * idx) / Math.max(1, ids.length);
    positions.set(id, {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
      vx: 0,
      vy: 0,
    });
  });

  // Relaxation loop.
  for (let iter = 0; iter < ITERATIONS; iter++) {
    // Repulsion between every pair.
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = positions.get(ids[i])!;
        const b = positions.get(ids[j])!;
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const distSq = Math.max(100, dx * dx + dy * dy);
        const force = REPEL / distSq;
        const dist = Math.sqrt(distSq);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx += fx;
        a.vy += fy;
        b.vx -= fx;
        b.vy -= fy;
      }
    }

    // Spring attraction along edges.
    for (const [src, , dst] of data.edges) {
      const a = positions.get(src);
      const b = positions.get(dst);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.max(1, Math.hypot(dx, dy));
      const stretch = dist - REST_LENGTH;
      const fx = (dx / dist) * stretch * SPRING;
      const fy = (dy / dist) * stretch * SPRING;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }

    // Integrate.
    for (const pt of positions.values()) {
      pt.vx *= DAMPING;
      pt.vy *= DAMPING;
      pt.x += pt.vx;
      pt.y += pt.vy;
      // Keep inside the canvas.
      pt.x = Math.max(24, Math.min(width - 24, pt.x));
      pt.y = Math.max(24, Math.min(height - 24, pt.y));
    }
  }

  return positions;
}
