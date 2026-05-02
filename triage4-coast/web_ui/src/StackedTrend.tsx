// Stacked-area chart: ok / watch / urgent counts over time across
// all zones. Reads from GET /coast/aggregates. Pure SVG.

import { useEffect, useState } from "react";
import { api, type AggregateBucket } from "./api";

const W = 900;
const H = 140;
const PAD = { top: 8, right: 8, bottom: 22, left: 36 };

const COLORS = { ok: "#27ae60", watch: "#e6a23c", urgent: "#e74c3c" };

export default function StackedTrend({
  hours = 4, bucketMinutes = 5, refreshMs = 15_000,
}: { hours?: number; bucketMinutes?: number; refreshMs?: number }) {
  const [buckets, setBuckets] = useState<AggregateBucket[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const fetch1 = async () => {
      try {
        const r = await api.coastAggregates(hours, bucketMinutes);
        if (alive) { setBuckets(r.buckets); setError(null); }
      } catch (e) {
        if (alive) setError((e as Error).message);
      }
    };
    fetch1();
    const t = setInterval(fetch1, refreshMs);
    return () => { alive = false; clearInterval(t); };
  }, [hours, bucketMinutes, refreshMs]);

  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const total = (b: AggregateBucket) => b.ok + b.watch + b.urgent;
  const maxTotal = buckets.length
    ? Math.max(1, ...buckets.map(total))
    : 1;

  const xFor = (i: number) =>
    PAD.left + (buckets.length > 1 ? (i / (buckets.length - 1)) * innerW : 0);
  const yFor = (cum: number) => PAD.top + innerH * (1 - cum / maxTotal);

  // Build cumulative paths for stacking
  const stack = buckets.map((b) => ({
    ts: b.ts_unix,
    cumOk: b.ok,
    cumWatch: b.ok + b.watch,
    cumAll: b.ok + b.watch + b.urgent,
  }));

  const areaPath = (
    upper: (s: typeof stack[number]) => number,
    lower: (s: typeof stack[number]) => number,
  ) => {
    if (stack.length === 0) return "";
    const top = stack.map((s, i) => `${xFor(i)},${yFor(upper(s))}`).join(" L");
    const bot = [...stack].reverse().map(
      (s, j) => `${xFor(stack.length - 1 - j)},${yFor(lower(s))}`,
    ).join(" L");
    return `M${top} L${bot} Z`;
  };

  return (
    <div style={{
      background: "#0e1422", borderRadius: 6, padding: 8, marginBottom: 16,
    }}>
      <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>
        zones-by-level over last {hours}h ({bucketMinutes}-min buckets)
      </div>
      {buckets.length === 0 ? (
        <div style={{
          height: H, display: "flex", alignItems: "center",
          justifyContent: "center", fontSize: 11, opacity: 0.6,
        }}>
          {error ? error : "(no samples yet — re-seed or run /camera/run)"}
        </div>
      ) : (
        <svg width="100%" viewBox={`0 0 ${W} ${H}`}
          style={{ display: "block" }}>
          {/* y-axis grid */}
          {[0, 0.25, 0.5, 0.75, 1.0].map((p) => (
            <g key={p}>
              <line x1={PAD.left} x2={W - PAD.right}
                y1={PAD.top + innerH * (1 - p)}
                y2={PAD.top + innerH * (1 - p)}
                stroke="#26304a" strokeWidth="0.5" />
              <text x={PAD.left - 4} y={PAD.top + innerH * (1 - p) + 3}
                textAnchor="end" fontSize="9" fill="#7a829a">
                {Math.round(maxTotal * p)}
              </text>
            </g>
          ))}
          {/* Stacked areas: bottom = urgent, middle = watch, top = ok */}
          <path d={areaPath((s) => s.cumAll, (s) => s.cumWatch)}
            fill={COLORS.urgent} fillOpacity="0.85" />
          <path d={areaPath((s) => s.cumWatch, (s) => s.cumOk)}
            fill={COLORS.watch} fillOpacity="0.85" />
          <path d={areaPath((s) => s.cumOk, () => 0)}
            fill={COLORS.ok} fillOpacity="0.85" />
          {/* x-axis labels — first / last */}
          <text x={PAD.left} y={H - 6} fontSize="9" fill="#7a829a">
            -{hours}h
          </text>
          <text x={W - PAD.right} y={H - 6}
            textAnchor="end" fontSize="9" fill="#7a829a">
            now
          </text>
          {/* Legend */}
          <g transform={`translate(${PAD.left + 4}, ${PAD.top + 4})`}>
            {(["urgent", "watch", "ok"] as const).map((k, i) => (
              <g key={k} transform={`translate(${i * 70}, 0)`}>
                <rect width="10" height="10" fill={COLORS[k]} />
                <text x="14" y="9" fontSize="10" fill="#dde7df">{k}</text>
              </g>
            ))}
          </g>
        </svg>
      )}
    </div>
  );
}
