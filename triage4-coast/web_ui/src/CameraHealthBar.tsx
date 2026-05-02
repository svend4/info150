// Compact camera-health status bar for the dashboard top.

import { useEffect, useState } from "react";
import { api, type CameraHealthRow } from "./api";

const STATE_COLOR: Record<CameraHealthRow["state"], string> = {
  ok: "#27ae60",
  stale: "#e6a23c",
  down: "#e74c3c",
  unknown: "#5c6080",
};

export default function CameraHealthBar({ refreshMs = 5000 }: { refreshMs?: number }) {
  const [rows, setRows] = useState<CameraHealthRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const fetch1 = async () => {
      try {
        const r = await api.camerasHealth();
        if (alive) { setRows(r.cameras); setError(null); }
      } catch (e) {
        if (alive) setError((e as Error).message);
      }
    };
    fetch1();
    const t = setInterval(fetch1, refreshMs);
    return () => { alive = false; clearInterval(t); };
  }, [refreshMs]);

  if (error) {
    return (
      <div style={{
        padding: "6px 10px", background: "#3a1a1a", borderRadius: 4,
        fontSize: 11, color: "#ff8c8c", marginBottom: 8,
      }}>
        cameras/health: {error}
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div style={{
        padding: "6px 10px", background: "#181f33", borderRadius: 4,
        fontSize: 11, color: "#7a829a", marginBottom: 8,
      }}>
        no camera reports yet — POST <code>/cameras/report</code> to register a feed
      </div>
    );
  }

  return (
    <div style={{
      display: "flex", gap: 8, flexWrap: "wrap", padding: 6,
      background: "#181f33", borderRadius: 4, marginBottom: 8,
    }}>
      {rows.map((r) => {
        const age = r.last_frame_ts_unix !== null
          ? Math.round(Date.now() / 1000 - r.last_frame_ts_unix)
          : null;
        return (
          <div key={r.source} style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "4px 8px", background: "#22293f", borderRadius: 4,
            border: `1px solid ${STATE_COLOR[r.state]}`,
            fontSize: 11,
          }}>
            <span style={{
              width: 8, height: 8, borderRadius: 4,
              background: STATE_COLOR[r.state],
            }} />
            <code style={{ fontSize: 10 }}>{r.source.length > 32
              ? "…" + r.source.slice(-30) : r.source}</code>
            <span style={{ opacity: 0.7 }}>
              {r.fps.toFixed(1)}fps · seen {r.frames_seen}
              {r.frames_dropped > 0 && (
                <span style={{ color: "#e6a23c" }}> · drops {r.frames_dropped}</span>
              )}
              {age !== null && <> · {age}s ago</>}
            </span>
          </div>
        );
      })}
    </div>
  );
}
