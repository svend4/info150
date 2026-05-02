// Mini canvas line-chart for one (zone, channel) history series.
// Zero external chart deps — keeps the bundle slim.

import { useEffect, useRef, useState } from "react";
import { api, type HistoryPoint } from "./api";

const W = 320;
const H = 80;
const PAD = 6;

export default function HistoryChart({
  zoneId, channel, hours = 1, refreshMs = 5000,
}: {
  zoneId: string; channel: string; hours?: number; refreshMs?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [points, setPoints] = useState<HistoryPoint[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const fetch1 = async () => {
      try {
        const r = await api.zoneHistory(zoneId, channel, hours);
        if (alive) { setPoints(r.points); setError(null); }
      } catch (e) {
        if (alive) setError((e as Error).message);
      }
    };
    fetch1();
    const t = setInterval(fetch1, refreshMs);
    return () => { alive = false; clearInterval(t); };
  }, [zoneId, channel, hours, refreshMs]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    // Canvas does NOT resolve CSS variables — read computed styles
    // off the document root so the chart re-themes correctly.
    const css = getComputedStyle(document.documentElement);
    const C = {
      border: css.getPropertyValue("--border").trim() || "#26304a",
      primary: css.getPropertyValue("--primary").trim() || "#5c7cfa",
      text: css.getPropertyValue("--text").trim() || "#dde7df",
    };
    ctx.clearRect(0, 0, W, H);

    // Frame
    ctx.strokeStyle = C.border;
    ctx.strokeRect(0.5, 0.5, W - 1, H - 1);
    // Reference lines at 0.3 / 0.7
    ctx.setLineDash([2, 4]);
    ctx.strokeStyle = C.border;
    for (const v of [0.3, 0.7]) {
      const y = H - PAD - (H - 2 * PAD) * v;
      ctx.beginPath();
      ctx.moveTo(PAD, y);
      ctx.lineTo(W - PAD, y);
      ctx.stroke();
    }
    ctx.setLineDash([]);

    if (points.length === 0) {
      ctx.fillStyle = C.primary;
      ctx.font = "11px system-ui";
      ctx.fillText("(no samples yet)", PAD + 2, H / 2 + 4);
      return;
    }

    // Map x to time, y to value [0, 1]
    const tmin = points[0].ts;
    const tmax = points[points.length - 1].ts;
    const tspan = Math.max(tmax - tmin, 1);
    const xy = points.map((p) => {
      const x = PAD + ((p.ts - tmin) / tspan) * (W - 2 * PAD);
      const y = H - PAD - Math.max(0, Math.min(1, p.value)) * (H - 2 * PAD);
      return { x, y, v: p.value };
    });

    ctx.strokeStyle = C.primary;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    xy.forEach((pt, i) => {
      if (i === 0) ctx.moveTo(pt.x, pt.y); else ctx.lineTo(pt.x, pt.y);
    });
    ctx.stroke();

    // Last value label
    const last = xy[xy.length - 1];
    ctx.fillStyle = C.text;
    ctx.font = "11px system-ui";
    ctx.fillText(last.v.toFixed(2), W - 30, last.y - 4);
  }, [points]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <div style={{ fontSize: 11, opacity: 0.7 }}>
        {channel} — last {hours}h ({points.length} samples)
      </div>
      <canvas ref={canvasRef} width={W} height={H}
        style={{ background: "var(--bg)", borderRadius: 4 }} />
      {error && (
        <div style={{ fontSize: 11, color: "var(--danger-text)" }}>{error}</div>
      )}
    </div>
  );
}
