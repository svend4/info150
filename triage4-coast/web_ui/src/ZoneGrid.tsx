// Multi-zone grid view — alternative to the single-detail layout.
// Shows every zone as a card with all four channel bars + alert pill,
// and a small inline overall-history sparkline.

import HistoryChart from "./HistoryChart";
import type { Score, AlertLevel } from "./types";

const LEVEL_COLOR: Record<AlertLevel, string> = {
  ok: "#27ae60", watch: "#e6a23c", urgent: "#e74c3c",
};

function ChannelBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = pct < 45 ? "#e74c3c" : pct < 65 ? "#e6a23c" : "#27ae60";
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11 }}>
        <span style={{ opacity: 0.75 }}>{label}</span>
        <span style={{ fontVariantNumeric: "tabular-nums" }}>{value.toFixed(2)}</span>
      </div>
      <div style={{ height: 4, background: "#2a3346", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, background: color, height: "100%" }} />
      </div>
    </div>
  );
}

export default function ZoneGrid({ scores }: { scores: Score[] }) {
  if (scores.length === 0) {
    return <div style={{ opacity: 0.6, padding: 16 }}><i>no zones</i></div>;
  }
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
      gap: 12,
    }}>
      {scores.map((s) => (
        <div key={s.zone_id} style={{
          background: "#181f33",
          border: `1px solid ${LEVEL_COLOR[s.alert_level]}`,
          borderLeft: `4px solid ${LEVEL_COLOR[s.alert_level]}`,
          borderRadius: 6, padding: 12,
        }}>
          <div style={{
            display: "flex", justifyContent: "space-between",
            alignItems: "baseline", marginBottom: 8,
          }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{s.zone_id}</div>
              <div style={{ fontSize: 11, opacity: 0.7 }}>{s.zone_kind}</div>
            </div>
            <div style={{
              padding: "2px 8px", borderRadius: 4, fontSize: 11,
              background: LEVEL_COLOR[s.alert_level], color: "#fff",
              fontWeight: 600, textTransform: "uppercase",
            }}>
              {s.alert_level} · {s.overall.toFixed(2)}
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 8 }}>
            <ChannelBar label="density" value={s.density_safety} />
            <ChannelBar label="drowning" value={s.drowning_safety} />
            <ChannelBar label="sun" value={s.sun_safety} />
            <ChannelBar label="lost-child" value={s.lost_child_safety} />
          </div>
          <HistoryChart zoneId={s.zone_id} channel="overall" hours={1} />
        </div>
      ))}
    </div>
  );
}
