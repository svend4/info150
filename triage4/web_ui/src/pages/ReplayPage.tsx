import { useEffect, useMemo, useState } from "react";

import type { ReplayData } from "../types";
import { priorityColor, scaleCoord } from "../util/priority";

export default function ReplayPage({ data }: { data: ReplayData | null }) {
  const [idx, setIdx] = useState(0);

  const frame = useMemo(() => {
    if (!data || data.frames.length === 0) return null;
    return data.frames[Math.min(idx, data.frames.length - 1)];
  }, [data, idx]);

  useEffect(() => {
    if (!data || data.frames.length === 0) return;
    const timer = setInterval(() => {
      setIdx((prev) => (prev + 1) % data.frames.length);
    }, 1100);
    return () => clearInterval(timer);
  }, [data]);

  if (!data || !frame) return <div>Loading replay…</div>;

  return (
    <div style={{ background: "#0e1528", borderRadius: 12, padding: 16 }}>
      <h3 style={{ marginTop: 0 }}>Replay Timeline</h3>
      <div style={{ marginBottom: 10, opacity: 0.85 }}>Frame: {frame.t}</div>

      <svg width="100%" viewBox="0 0 520 520" style={{ background: "#0a1020", borderRadius: 10 }}>
        <rect x="0" y="0" width="520" height="520" fill="#0a1020" />

        {frame.casualties.map((c) => (
          <g key={c.id}>
            <circle cx={scaleCoord(c.x)} cy={scaleCoord(c.y)} r={6} fill={priorityColor(c.priority)} />
            <text x={scaleCoord(c.x) + 8} y={scaleCoord(c.y) - 6} fill="#e5ecff" fontSize="12">
              {c.id}
            </text>
          </g>
        ))}

        {frame.platforms.map((p) => (
          <g key={p.id}>
            <rect x={scaleCoord(p.x) - 7} y={scaleCoord(p.y) - 7} width={14} height={14} fill="#4fc3f7" rx={3} />
            <text x={scaleCoord(p.x) + 10} y={scaleCoord(p.y) + 4} fill="#9cc7ff" fontSize="12">
              {p.id}
            </text>
          </g>
        ))}
      </svg>
    </div>
  );
}
