import type { MapData } from "../types";
import { priorityColor, scaleCoord } from "../util/priority";

export default function MapPage({ data }: { data: MapData | null }) {
  if (!data) return <div>Loading map…</div>;

  return (
    <div style={{ background: "#0e1528", borderRadius: 12, padding: 16 }}>
      <h3 style={{ marginTop: 0 }}>Tactical Map</h3>

      <svg width="100%" viewBox="0 0 520 520" style={{ background: "#0a1020", borderRadius: 10 }}>
        <rect x="0" y="0" width="520" height="520" fill="#0a1020" />

        {[...Array(11)].map((_, i) => (
          <g key={i}>
            <line x1={i * 52} y1={0} x2={i * 52} y2={520} stroke="#1b2945" strokeWidth="1" />
            <line x1={0} y1={i * 52} x2={520} y2={i * 52} stroke="#1b2945" strokeWidth="1" />
          </g>
        ))}

        {data.casualties.map((c) => (
          <g key={c.id}>
            <circle cx={scaleCoord(c.x)} cy={scaleCoord(c.y)} r={18} fill={priorityColor(c.priority)} opacity={0.15} />
            <circle cx={scaleCoord(c.x)} cy={scaleCoord(c.y)} r={7} fill={priorityColor(c.priority)} />
            <text x={scaleCoord(c.x) + 10} y={scaleCoord(c.y) - 8} fill="#e5ecff" fontSize="12">
              {c.id}
            </text>
          </g>
        ))}

        {data.platforms.map((p) => (
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
