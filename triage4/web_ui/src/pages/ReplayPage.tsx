// Replay tab: scrubber + play/pause + speed control over the
// backend /replay timeline.

import { useEffect, useMemo, useRef, useState } from "react";

import { fetchReplay } from "../api/endpoints";
import MapLegend from "../components/map/MapLegend";
import TacticalMap from "../components/map/TacticalMap";
import { useResource } from "../hooks/useResource";

const SPEEDS = [0.5, 1, 2, 4];

export default function ReplayPage() {
  const { data, error, loading, refresh } = useResource(fetchReplay);
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(1);
  const timerRef = useRef<number | undefined>(undefined);

  const frames = data?.frames ?? [];
  const frame = frames[Math.min(idx, Math.max(0, frames.length - 1))] ?? null;

  const baseInterval = 1100;

  useEffect(() => {
    if (!playing || frames.length === 0) return;
    timerRef.current = window.setInterval(() => {
      setIdx((prev) => (prev + 1) % frames.length);
    }, Math.max(100, baseInterval / speed));
    return () => {
      if (timerRef.current !== undefined) window.clearInterval(timerRef.current);
    };
  }, [playing, speed, frames.length]);

  const first = useMemo(() => (frames.length > 0 ? frames[0].t : 0), [frames]);
  const last = useMemo(
    () => (frames.length > 0 ? frames[frames.length - 1].t : 0),
    [frames],
  );

  return (
    <section style={{ maxWidth: 1100, margin: "0 auto" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 16,
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Mission replay</h1>
          <div
            style={{ color: "var(--text-2)", fontSize: 12, marginTop: 4 }}
          >
            Timeline of {frames.length} frame{frames.length === 1 ? "" : "s"}
            {" "}from t={first} to t={last}.
          </div>
        </div>
        <button onClick={refresh} disabled={loading}>
          refresh
        </button>
      </header>

      {error && (
        <div
          style={{
            padding: 12,
            border: "1px solid var(--err)",
            borderRadius: "var(--r2)",
            color: "var(--err)",
            marginBottom: 16,
          }}
        >
          {error.message}
        </div>
      )}

      <div style={{ marginBottom: 12 }}>
        <MapLegend />
      </div>

      {frame ? (
        <>
          <TacticalMap
            platforms={frame.platforms}
            casualties={frame.casualties}
          />
          <div
            style={{
              marginTop: 12,
              padding: 12,
              background: "var(--bg-1)",
              border: "1px solid var(--border-1)",
              borderRadius: "var(--r2)",
            }}
          >
            <div
              style={{
                display: "flex",
                gap: 10,
                alignItems: "center",
                marginBottom: 10,
              }}
            >
              <button
                onClick={() => setPlaying((p) => !p)}
                aria-label={playing ? "pause" : "play"}
              >
                {playing ? "⏸ pause" : "▶ play"}
              </button>
              <button
                onClick={() => setIdx(0)}
                aria-label="rewind"
              >
                ⏮ rewind
              </button>
              <button
                onClick={() =>
                  setIdx((i) => Math.max(0, i - 1))
                }
                disabled={idx <= 0}
              >
                ← step
              </button>
              <button
                onClick={() =>
                  setIdx((i) => Math.min(frames.length - 1, i + 1))
                }
                disabled={idx >= frames.length - 1}
              >
                step →
              </button>
              <span style={{ marginLeft: 12, color: "var(--text-2)", fontSize: 12 }}>
                speed
              </span>
              {SPEEDS.map((s) => (
                <button
                  key={s}
                  aria-pressed={speed === s}
                  onClick={() => setSpeed(s)}
                  style={{ fontSize: 11, padding: "4px 8px" }}
                >
                  {s}×
                </button>
              ))}
              <span
                style={{
                  marginLeft: "auto",
                  fontFamily: "var(--font-mono)",
                  fontSize: 12,
                  color: "var(--text-1)",
                }}
              >
                frame {idx + 1} / {frames.length} · t = {frame.t}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={Math.max(0, frames.length - 1)}
              value={idx}
              onChange={(e) => {
                setPlaying(false);
                setIdx(Number(e.target.value));
              }}
            />
          </div>
        </>
      ) : (
        <div style={{ color: "var(--text-2)", fontStyle: "italic" }}>
          loading timeline…
        </div>
      )}
    </section>
  );
}
