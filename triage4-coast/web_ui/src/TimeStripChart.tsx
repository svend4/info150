// 24-hour horizontal strip chart of one zone's overall score.
// Each cell = 1 hour, coloured by the hourly mean. Reads from the
// new GET /zones/{id}/hourly endpoint.

import { useEffect, useState } from "react";
import { api, type HourlyBucket } from "./api";

const W = 900;
const ROW_H = 22;
const LABEL_W = 130;

function colorFor(value: number | null): string {
  if (value === null) return "#1a1f2e";
  if (value < 0.45) return "#e74c3c";
  if (value < 0.65) return "#e6a23c";
  return "#27ae60";
}

export default function TimeStripChart({
  zoneIds, hours = 24, refreshMs = 30_000,
}: {
  zoneIds: string[]; hours?: number; refreshMs?: number;
}) {
  const [byZone, setByZone] = useState<Record<string, HourlyBucket[]>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const fetchAll = async () => {
      try {
        const out: Record<string, HourlyBucket[]> = {};
        for (const z of zoneIds) {
          const r = await api.zoneHourly(z, "overall", hours);
          out[z] = r.buckets;
        }
        if (alive) { setByZone(out); setError(null); }
      } catch (e) {
        if (alive) setError((e as Error).message);
      }
    };
    fetchAll();
    const t = setInterval(fetchAll, refreshMs);
    return () => { alive = false; clearInterval(t); };
  }, [JSON.stringify(zoneIds), hours, refreshMs]);

  const totalH = ROW_H * zoneIds.length + 30;
  const cellW = (W - LABEL_W - 12) / hours;

  return (
    <div style={{
      background: "#0e1422", borderRadius: 6, padding: 8, marginBottom: 16,
    }}>
      <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 4 }}>
        last {hours} h, hourly mean of overall (red = urgent, green = ok)
      </div>
      <svg width="100%" viewBox={`0 0 ${W} ${totalH}`}
        style={{ display: "block" }}>
        {/* x-axis (hours-ago) */}
        {Array.from({ length: hours + 1 }, (_, i) => i).map((i) => (
          i % 4 === 0 && (
            <text key={i}
              x={W - 6 - i * cellW} y={totalH - 8}
              textAnchor="middle" fontSize="9" fill="#7a829a">
              -{i}h
            </text>
          )
        ))}
        {zoneIds.map((z, row) => {
          const buckets = byZone[z] || [];
          const lookup: Record<number, number> = {};
          for (const b of buckets) lookup[b.hour_ago] = b.mean_value;
          return (
            <g key={z}>
              <text x={LABEL_W - 8} y={row * ROW_H + ROW_H * 0.7}
                textAnchor="end" fontSize="11" fill="#dde7df"
                fontFamily="monospace">
                {z.slice(0, 16)}
              </text>
              {Array.from({ length: hours }, (_, i) => i).map((i) => {
                const v = lookup[i] ?? null;
                const x = W - 6 - (i + 1) * cellW;
                return (
                  <rect key={i}
                    x={x} y={row * ROW_H + 4}
                    width={cellW - 1} height={ROW_H - 6}
                    fill={colorFor(v)}
                    opacity={v === null ? 0.3 : 1}>
                    <title>
                      {z} · -{i}h · {v === null ? "no data" : v.toFixed(2)}
                    </title>
                  </rect>
                );
              })}
            </g>
          );
        })}
      </svg>
      {error && (
        <div style={{ fontSize: 11, color: "#ff8c8c" }}>{error}</div>
      )}
    </div>
  );
}
