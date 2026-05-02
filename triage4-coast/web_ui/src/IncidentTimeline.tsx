// Chronological audit log of operator broadcasts. Newest first.
// Reads from GET /broadcast/log every 10 s.

import { useEffect, useState } from "react";
import { api, type BroadcastEntry } from "./api";

const KIND_ICON: Record<string, string> = {
  shade_advisory: "🌳",
  lost_child: "🚸",
  clear_water: "🌊",
  lightning: "⚡",
  general_announcement: "📣",
};

function fmtAge(secAgo: number): string {
  if (secAgo < 60) return `${Math.round(secAgo)}s ago`;
  if (secAgo < 3600) return `${Math.round(secAgo / 60)}m ago`;
  if (secAgo < 86400) return `${Math.round(secAgo / 3600)}h ago`;
  return `${Math.round(secAgo / 86400)}d ago`;
}

export default function IncidentTimeline({ refreshMs = 10_000 }: { refreshMs?: number }) {
  const [entries, setEntries] = useState<BroadcastEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    const fetch1 = async () => {
      try {
        const r = await api.broadcastLog(50);
        if (alive) { setEntries(r.entries); setError(null); }
      } catch (e) {
        if (alive) setError((e as Error).message);
      }
    };
    fetch1();
    const t = setInterval(fetch1, refreshMs);
    return () => { alive = false; clearInterval(t); };
  }, [refreshMs]);

  const now = Date.now() / 1000;

  return (
    <div style={{
      background: "var(--bg)", borderRadius: 6, padding: 8,
      maxHeight: 320, overflowY: "auto",
    }}>
      <div style={{
        fontSize: 11, opacity: 0.7, marginBottom: 4,
        position: "sticky", top: 0, background: "var(--bg)",
        paddingBottom: 4,
      }}>
        operator log ({entries.length})
      </div>
      {entries.length === 0 ? (
        <div style={{
          fontSize: 11, opacity: 0.6, padding: 8,
        }}>
          (no broadcasts yet — issue one from the panel)
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {entries.map((e, i) => (
            <div key={i} style={{
              padding: 8, background: "var(--surface)", borderRadius: 4,
              borderLeft: "3px solid var(--primary)",
            }}>
              <div style={{
                display: "flex", justifyContent: "space-between",
                alignItems: "baseline", fontSize: 11,
              }}>
                <span style={{ fontWeight: 600 }}>
                  {KIND_ICON[e.kind] || "•"} {e.kind}
                </span>
                <span style={{ opacity: 0.6 }}>
                  {fmtAge(now - e.ts_unix)}
                </span>
              </div>
              <div style={{ fontSize: 12, marginTop: 2 }}>{e.message}</div>
              <div style={{ fontSize: 10, opacity: 0.6, marginTop: 2 }}>
                {e.zone_id ? `zone: ${e.zone_id}` : "all zones"}
                {e.operator_id && ` · op: ${e.operator_id}`}
              </div>
            </div>
          ))}
        </div>
      )}
      {error && (
        <div style={{ fontSize: 11, color: "var(--danger-text)" }}>{error}</div>
      )}
    </div>
  );
}
