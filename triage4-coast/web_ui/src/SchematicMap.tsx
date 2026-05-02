// SVG schematic of a coast strip — zones laid out left-to-right with
// colour by alert level. Click a zone to select it. Pure SVG, no
// external chart libraries. Designed to be scannable at a glance:
// the operator should be able to spot the urgent zone in <0.5 s.

import type { AlertLevel, Score } from "./types";

const LEVEL_COLOR: Record<AlertLevel, string> = {
  ok: "#27ae60", watch: "#e6a23c", urgent: "#e74c3c",
};

const ZONE_KIND_GLYPH: Record<string, string> = {
  beach: "🏖", promenade: "🚶", water: "🌊", pier: "🛶",
};

export default function SchematicMap({
  scores, selected, onSelect,
}: {
  scores: Score[];
  selected: string | null;
  onSelect: (zoneId: string) => void;
}) {
  const W = 900;
  const H = 160;
  const margin = 16;
  const gap = 12;
  if (scores.length === 0) {
    return <div style={{ opacity: 0.6, padding: 16 }}><i>no zones</i></div>;
  }
  const tileW = (W - 2 * margin - (scores.length - 1) * gap) / scores.length;

  return (
    <div style={{
      background: "#0e1422", borderRadius: 6, padding: 8, marginBottom: 16,
    }}>
      <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>
        coast schematic — click a zone for details
      </div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`}
        style={{ display: "block" }}>
        {/* Sea band at the bottom */}
        <rect x="0" y={H - 24} width={W} height="24" fill="#13243a" />
        {/* Land band at top */}
        <rect x="0" y="0" width={W} height={H - 24} fill="#1a1f2e" />
        {scores.map((s, i) => {
          const x = margin + i * (tileW + gap);
          const isSelected = selected === s.zone_id;
          const color = LEVEL_COLOR[s.alert_level];
          // Pulse halo for urgent zones
          const pulse = s.alert_level === "urgent";
          return (
            <g key={s.zone_id}
              onClick={() => onSelect(s.zone_id)}
              style={{ cursor: "pointer" }}>
              {pulse && (
                <rect x={x - 4} y={20} width={tileW + 8} height={H - 60}
                  fill="none" stroke={color} strokeWidth="2"
                  opacity="0.4" rx="6">
                  <animate attributeName="opacity"
                    values="0.7;0.2;0.7" dur="1.6s"
                    repeatCount="indefinite" />
                </rect>
              )}
              <rect x={x} y="24" width={tileW} height={H - 56}
                fill={isSelected ? "#222a3e" : "#181f33"}
                stroke={color} strokeWidth={isSelected ? 3 : 2} rx="4" />
              {/* Glyph */}
              <text x={x + tileW / 2} y="56"
                textAnchor="middle" fontSize="22"
                fill="#dde7df">
                {ZONE_KIND_GLYPH[s.zone_kind] || "•"}
              </text>
              {/* Zone id */}
              <text x={x + tileW / 2} y="80"
                textAnchor="middle" fontSize="11"
                fill="#dde7df" fontFamily="monospace">
                {s.zone_id.slice(0, 18)}
              </text>
              {/* Level pill */}
              <rect x={x + 8} y="92" width={tileW - 16} height="14"
                fill={color} rx="3" opacity="0.85" />
              <text x={x + tileW / 2} y="103"
                textAnchor="middle" fontSize="10"
                fill="#fff" fontWeight="600">
                {s.alert_level.toUpperCase()} · {s.overall.toFixed(2)}
              </text>
              {/* Mini channel bars (4 thin lines) */}
              {[s.density_safety, s.drowning_safety, s.sun_safety,
                s.lost_child_safety].map((v, j) => (
                <rect key={j}
                  x={x + 8 + j * ((tileW - 24) / 4 + 4)}
                  y={114 + (1 - v) * 18}
                  width={(tileW - 32) / 4}
                  height={2 + v * 18}
                  fill={v < 0.45 ? "#e74c3c"
                    : v < 0.65 ? "#e6a23c" : "#27ae60"} />
              ))}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
