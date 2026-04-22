import { usePolling } from "../../hooks/usePolling";
import { fetchHealth } from "../../api/endpoints";
import { formatAge } from "../../util/format";

const STYLE_DOT = (color: string): React.CSSProperties => ({
  width: 10,
  height: 10,
  borderRadius: "50%",
  background: color,
  display: "inline-block",
});

export default function HealthBadge() {
  const { data, error, lastFetch } = usePolling(fetchHealth, 5000);
  const colour =
    error !== null ? "var(--err)" : data?.ok ? "var(--ok)" : "var(--warn)";
  const text =
    error !== null
      ? `offline (${error.status || "—"})`
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
