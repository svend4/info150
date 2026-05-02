// Composite heat-stress index gauge — sum of (1−sun_safety) × density.
// Shown as a 270° arc gauge with a needle. Designed to be glance-able:
// red wedge above 0.7 = "tell people to seek shade".

import type { Score } from "./types";

const SIZE = 220;
const CENTER = SIZE / 2;
const R = SIZE * 0.38;
const STROKE = 14;

function heatStressIndex(scores: Score[]): { value: number; reason: string } {
  if (scores.length === 0) return { value: 0, reason: "(no zones)" };
  // Risk per zone = (1 - sun_safety) × density_pressure_proxy (= 1-density_safety)
  let total = 0;
  let worstZone = scores[0].zone_id;
  let worstRisk = 0;
  for (const s of scores) {
    const risk = (1 - s.sun_safety) * (1 - s.density_safety);
    if (risk > worstRisk) { worstRisk = risk; worstZone = s.zone_id; }
    total += risk;
  }
  return {
    value: Math.min(1, total / scores.length * 2),  // scaled
    reason: `worst: ${worstZone} (risk ${worstRisk.toFixed(2)})`,
  };
}

function arcPath(startDeg: number, endDeg: number): string {
  // Convert to radians; rotate so 0 = top, sweep clockwise.
  const toRad = (d: number) => (d - 90) * Math.PI / 180;
  const [sx, sy] = [
    CENTER + R * Math.cos(toRad(startDeg)),
    CENTER + R * Math.sin(toRad(startDeg)),
  ];
  const [ex, ey] = [
    CENTER + R * Math.cos(toRad(endDeg)),
    CENTER + R * Math.sin(toRad(endDeg)),
  ];
  const largeArc = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
  return `M ${sx} ${sy} A ${R} ${R} 0 ${largeArc} 1 ${ex} ${ey}`;
}

export default function HeatStressGauge({ scores }: { scores: Score[] }) {
  const { value, reason } = heatStressIndex(scores);
  // Gauge sweeps from -135° to +135° (270° total).
  const startDeg = -135, endDeg = 135;
  const span = endDeg - startDeg;
  const needleDeg = startDeg + span * value;
  const needleRad = (needleDeg - 90) * Math.PI / 180;
  const [nx, ny] = [
    CENTER + R * Math.cos(needleRad),
    CENTER + R * Math.sin(needleRad),
  ];
  const status =
    value >= 0.7 ? { color: "#e74c3c", label: "HIGH" }
      : value >= 0.4 ? { color: "#e6a23c", label: "MODERATE" }
        : { color: "#27ae60", label: "LOW" };

  // Pulse halo for HIGH
  const pulse = value >= 0.7;

  return (
    <div style={{ background: "#0e1422", borderRadius: 6, padding: 8 }}>
      <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>
        heat-stress index — sun × density × time
      </div>
      <svg width={SIZE} height={SIZE}>
        {/* Gauge backdrop arc */}
        <path d={arcPath(startDeg, endDeg)}
          stroke="#26304a" strokeWidth={STROKE} fill="none"
          strokeLinecap="round" />
        {/* Coloured zones */}
        <path d={arcPath(startDeg, startDeg + span * 0.4)}
          stroke="#27ae60" strokeWidth={STROKE} fill="none"
          strokeLinecap="round" opacity="0.65" />
        <path d={arcPath(startDeg + span * 0.4, startDeg + span * 0.7)}
          stroke="#e6a23c" strokeWidth={STROKE} fill="none"
          strokeLinecap="round" opacity="0.65" />
        <path d={arcPath(startDeg + span * 0.7, endDeg)}
          stroke="#e74c3c" strokeWidth={STROKE} fill="none"
          strokeLinecap="round" opacity="0.65" />
        {/* Needle */}
        <line x1={CENTER} y1={CENTER} x2={nx} y2={ny}
          stroke={status.color} strokeWidth="3" strokeLinecap="round" />
        <circle cx={CENTER} cy={CENTER} r="6"
          fill={status.color} />
        {pulse && (
          <circle cx={CENTER} cy={CENTER} r="14"
            fill="none" stroke="#e74c3c" strokeWidth="2"
            opacity="0.5">
            <animate attributeName="r"
              values="14;28;14" dur="1.6s" repeatCount="indefinite" />
            <animate attributeName="opacity"
              values="0.6;0.1;0.6" dur="1.6s" repeatCount="indefinite" />
          </circle>
        )}
        {/* Numeric value */}
        <text x={CENTER} y={CENTER + R - 18}
          textAnchor="middle" fontSize="22" fontWeight="700"
          fill={status.color}>
          {value.toFixed(2)}
        </text>
        <text x={CENTER} y={CENTER + R + 4}
          textAnchor="middle" fontSize="11" fill="#dde7df"
          letterSpacing="1">
          {status.label}
        </text>
      </svg>
      <div style={{ fontSize: 11, opacity: 0.6, marginTop: 4 }}>
        {reason}
      </div>
    </div>
  );
}
