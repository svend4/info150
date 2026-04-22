// Horizontal confidence bar with value in the label.

import { formatPercent } from "../../util/format";

type Props = {
  label: string;
  value: number; // 0..1
  color?: string;
  showValue?: boolean;
};

export default function ConfidenceBar({
  label,
  value,
  color = "var(--accent)",
  showValue = true,
}: Props) {
  const clamped = Math.max(0, Math.min(1, value));
  return (
    <div style={{ marginBottom: 6 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 12,
          color: "var(--text-1)",
          marginBottom: 2,
        }}
      >
        <span>{label}</span>
        {showValue && (
          <span style={{ fontFamily: "var(--font-mono)" }}>
            {formatPercent(clamped, 0)}
          </span>
        )}
      </div>
      <div
        style={{
          height: 6,
          background: "var(--bg-1)",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${clamped * 100}%`,
            height: "100%",
            background: color,
            transition: "width 0.2s",
          }}
        />
      </div>
    </div>
  );
}
