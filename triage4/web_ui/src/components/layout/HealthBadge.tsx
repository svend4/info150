import { useEffect, useRef } from "react";

import { usePolling } from "../../hooks/usePolling";
import { fetchHealth } from "../../api/endpoints";
import { useToast } from "../../state/ToastContext";
import { formatAge } from "../../util/format";

const STYLE_DOT = (color: string): React.CSSProperties => ({
  width: 10,
  height: 10,
  borderRadius: "50%",
  background: color,
  display: "inline-block",
});

type HealthState = "ok" | "degraded" | "offline";

function classify(
  data: { ok: boolean } | null,
  error: unknown | null,
): HealthState {
  if (error) return "offline";
  if (data && data.ok) return "ok";
  return "degraded";
}

export default function HealthBadge() {
  const { data, error, lastFetch } = usePolling(fetchHealth, 5000);
  const state = classify(data, error);
  const toast = useToast();
  const prevRef = useRef<HealthState | null>(null);

  useEffect(() => {
    if (prevRef.current !== null && prevRef.current !== state) {
      if (state === "offline") {
        toast.push("Backend went offline", "error", 5000);
      } else if (state === "degraded") {
        toast.push("Backend degraded", "warn", 4000);
      } else {
        toast.push("Backend back online", "success", 2500);
      }
    }
    prevRef.current = state;
  }, [state, toast]);

  const colour =
    state === "offline"
      ? "var(--err)"
      : state === "ok"
        ? "var(--ok)"
        : "var(--warn)";
  const text =
    state === "offline"
      ? `offline${error && typeof error === "object" && "status" in error ? ` (${(error as { status: number }).status || "—"})` : ""}`
      : data
        ? `backend OK · ${data.nodes} nodes`
        : "connecting…";

  return (
    <div
      title={`last poll: ${formatAge(lastFetch)}`}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "4px 12px",
        background: "var(--bg-1)",
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r1)",
        fontFamily: "var(--font-mono)",
        fontSize: 12,
      }}
    >
      <span style={STYLE_DOT(colour)} />
      <span>{text}</span>
    </div>
  );
}
