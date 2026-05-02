// Operator broadcast panel — issues a placeholder advisory to the
// audit log. In production this would also push to a PA system,
// SMS gateway, or mobile-app webhook (operator integration TBD).

import { useState } from "react";
import { api } from "./api";

const KINDS: { kind: string; icon: string; label: string; defaultMsg: string }[] = [
  { kind: "shade_advisory", icon: "🌳", label: "Shade advisory",
    defaultMsg: "High sun + crowd density. Encourage shade and water." },
  { kind: "lost_child", icon: "🚸", label: "Lost child",
    defaultMsg: "Possible unaccompanied child. Lifeguard visual check." },
  { kind: "clear_water", icon: "🌊", label: "Clear water",
    defaultMsg: "Clear the swim zone — lifeguard rotation in progress." },
  { kind: "lightning", icon: "⚡", label: "Lightning",
    defaultMsg: "Lightning detected — clear water and pier immediately." },
  { kind: "general_announcement", icon: "📣", label: "Announcement",
    defaultMsg: "" },
];

export default function BroadcastPanel({
  zoneIds, onSent,
}: {
  zoneIds: string[];
  onSent: () => void;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const [zoneId, setZoneId] = useState<string>("");
  const [operatorId, setOperatorId] = useState<string>("");
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);

  const send = async (kind: string) => {
    setError(null);
    try {
      await api.broadcastSend({
        kind,
        message: message.trim() || (
          KINDS.find((k) => k.kind === kind)?.defaultMsg || "(no message)"
        ),
        zone_id: zoneId.trim() || null,
        operator_id: operatorId.trim() || null,
      });
      setSent(`${kind} sent`);
      setMessage("");
      setOpen(null);
      onSent();
      setTimeout(() => setSent(null), 3000);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div style={{
      background: "#0e1422", borderRadius: 6, padding: 12, marginBottom: 16,
    }}>
      <div style={{
        display: "flex", justifyContent: "space-between",
        alignItems: "baseline", marginBottom: 8,
      }}>
        <div style={{ fontSize: 13, fontWeight: 600 }}>Broadcast</div>
        <div style={{ fontSize: 11, opacity: 0.6 }}>
          one click — logs to audit; integrate with PA/SMS at deploy
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {KINDS.map((k) => (
          <button key={k.kind}
            onClick={() => setOpen(open === k.kind ? null : k.kind)}
            style={{
              padding: "10px 14px",
              background: open === k.kind ? "#5c7cfa" : "#181f33",
              color: "#dde7df", border: "1px solid #5c7cfa",
              borderRadius: 4, cursor: "pointer", fontSize: 13,
            }}>
            {k.icon} {k.label}
          </button>
        ))}
      </div>
      {open && (
        <div style={{ marginTop: 12, padding: 12,
          background: "#181f33", borderRadius: 4 }}>
          <div style={{ fontSize: 11, opacity: 0.7, marginBottom: 6 }}>
            issuing: <b>{open}</b>
          </div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap",
            marginBottom: 8 }}>
            <select value={zoneId} onChange={(e) => setZoneId(e.target.value)}
              style={{ padding: 6, background: "#22293f", color: "#dde7df",
                border: "1px solid #5c7cfa", borderRadius: 4 }}>
              <option value="">all zones</option>
              {zoneIds.map((z) => <option key={z} value={z}>{z}</option>)}
            </select>
            <input placeholder="operator id (optional)"
              value={operatorId} onChange={(e) => setOperatorId(e.target.value)}
              style={{ padding: 6, width: 180, background: "#22293f",
                color: "#dde7df", border: "1px solid #5c7cfa", borderRadius: 4 }} />
          </div>
          <textarea placeholder={
            KINDS.find((k) => k.kind === open)?.defaultMsg || "Message"
          }
            value={message} onChange={(e) => setMessage(e.target.value)}
            rows={2}
            style={{ width: "100%", padding: 6, background: "#22293f",
              color: "#dde7df", border: "1px solid #5c7cfa", borderRadius: 4,
              fontFamily: "inherit", fontSize: 13, boxSizing: "border-box" }} />
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button onClick={() => send(open)}
              style={{ padding: "6px 14px", background: "#3a8443",
                color: "#fff", border: 0, borderRadius: 4, cursor: "pointer" }}>
              Send broadcast
            </button>
            <button onClick={() => setOpen(null)}
              style={{ padding: "6px 14px", background: "#22293f",
                color: "#dde7df", border: "1px solid #444",
                borderRadius: 4, cursor: "pointer" }}>
              Cancel
            </button>
          </div>
        </div>
      )}
      {sent && (
        <div style={{ marginTop: 8, fontSize: 12, color: "#27ae60" }}>
          ✓ {sent}
        </div>
      )}
      {error && (
        <div style={{ marginTop: 8, fontSize: 12, color: "#ff8c8c" }}>
          {error}
        </div>
      )}
    </div>
  );
}
