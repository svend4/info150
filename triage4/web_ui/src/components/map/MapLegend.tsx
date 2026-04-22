import { priorityColor } from "../../util/priority";

export default function MapLegend() {
  return (
    <div
      style={{
        display: "flex",
        gap: 16,
        flexWrap: "wrap",
        padding: 10,
        background: "var(--bg-1)",
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r2)",
        fontSize: 12,
      }}
    >
      <strong
        style={{
          fontSize: 11,
          letterSpacing: 1,
          textTransform: "uppercase",
          color: "var(--text-2)",
        }}
      >
        legend
      </strong>
      {["immediate", "delayed", "minimal", "unknown"].map((p) => (
        <span
          key={p}
          style={{ display: "flex", alignItems: "center", gap: 6 }}
        >
          <svg width={14} height={14}>
            <circle cx={7} cy={7} r={4} fill={priorityColor(p)} />
          </svg>
          {p}
        </span>
      ))}
      <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <svg width={14} height={14}>
          <polygon points="7,2 12,12 2,12" fill="var(--accent)" />
        </svg>
        platform
      </span>
      <span style={{ color: "var(--text-2)", marginLeft: "auto" }}>
        scroll to zoom · drag to pan · double-click to reset
      </span>
    </div>
  );
}
