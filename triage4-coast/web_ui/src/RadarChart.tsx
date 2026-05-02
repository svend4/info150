// Spider / radar chart for one zone's 4 channels. Compact (200x200)
// — fits beside the schematic map. Pure SVG, no chart library.

import type { Score } from "./types";

const SIZE = 220;
const CENTER = SIZE / 2;
const RADIUS = SIZE * 0.36;

const AXES = [
  { key: "density_safety", label: "density" },
  { key: "drowning_safety", label: "drowning" },
  { key: "sun_safety", label: "sun" },
  { key: "lost_child_safety", label: "child" },
] as const;

function point(angle: number, r: number): [number, number] {
  return [
    CENTER + r * Math.cos(angle),
    CENTER + r * Math.sin(angle),
  ];
}

export default function RadarChart({ score }: { score: Score | null }) {
  if (!score) {
    return (
      <div style={{
        width: SIZE, height: SIZE, background: "#0e1422", borderRadius: 6,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 11, opacity: 0.6,
      }}>
        select a zone
      </div>
    );
  }

  const values = AXES.map((a) => Number(score[a.key as keyof Score]) || 0);
  const angles = AXES.map((_, i) => -Math.PI / 2 + (2 * Math.PI * i) / AXES.length);

  // Polygon for the value
  const polyPts = values.map((v, i) => point(angles[i], RADIUS * v))
    .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");

  return (
    <div style={{ background: "#0e1422", borderRadius: 6, padding: 8 }}>
      <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>
        {score.zone_id} — channel safety radar
      </div>
      <svg width={SIZE} height={SIZE}>
        {/* Concentric reference rings */}
        {[0.25, 0.5, 0.75, 1.0].map((r) => (
          <circle key={r}
            cx={CENTER} cy={CENTER} r={RADIUS * r}
            fill="none" stroke="#26304a" strokeWidth="0.5" />
        ))}
        {/* Axes */}
        {angles.map((a, i) => {
          const [x, y] = point(a, RADIUS);
          return (
            <line key={i}
              x1={CENTER} y1={CENTER} x2={x} y2={y}
              stroke="#26304a" strokeWidth="0.5" />
          );
        })}
        {/* Value polygon */}
        <polygon points={polyPts}
          fill="#5c7cfa" fillOpacity="0.25"
          stroke="#5c7cfa" strokeWidth="2" />
        {/* Value dots */}
        {values.map((v, i) => {
          const [x, y] = point(angles[i], RADIUS * v);
          const color = v < 0.45 ? "#e74c3c"
            : v < 0.65 ? "#e6a23c" : "#27ae60";
          return (
            <circle key={i} cx={x} cy={y} r="4" fill={color} />
          );
        })}
        {/* Axis labels */}
        {angles.map((a, i) => {
          const [x, y] = point(a, RADIUS + 18);
          return (
            <text key={i} x={x} y={y}
              textAnchor="middle" dominantBaseline="middle"
              fontSize="10" fill="#dde7df">
              {AXES[i].label}
              <tspan x={x} dy="11" fontSize="9" fill="#7a829a">
                {values[i].toFixed(2)}
              </tspan>
            </text>
          );
        })}
        {/* Center overall */}
        <text x={CENTER} y={CENTER}
          textAnchor="middle" dominantBaseline="middle"
          fontSize="14" fontWeight="600" fill="#dde7df">
          {score.overall.toFixed(2)}
        </text>
      </svg>
    </div>
  );
}
