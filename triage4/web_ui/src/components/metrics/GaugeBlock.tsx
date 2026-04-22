import type { MetricFamily } from "../../types";

type Props = { family: MetricFamily };

export default function GaugeBlock({ family }: Props) {
  return (
    <div
      style={{
        padding: 14,
        background: "var(--bg-1)",
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r2)",
      }}
    >
      <div
        style={{
          fontSize: 12,
          color: "var(--text-2)",
          textTransform: "uppercase",
          letterSpacing: 1,
          marginBottom: 2,
        }}
      >
        gauge
      </div>
      <div
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: 13,
          marginBottom: 10,
        }}
      >
        {family.name}
      </div>
      {family.help && (
        <div
          style={{
            fontSize: 12,
            color: "var(--text-1)",
            marginBottom: 10,
          }}
        >
          {family.help}
        </div>
      )}
      <div style={{ display: "grid", gap: 6 }}>
        {family.samples.map((s, idx) => {
          const labelStr = Object.keys(s.labels).length
            ? Object.entries(s.labels)
                .map(([k, v]) => `${k}=${v}`)
                .join(" ")
            : "(no labels)";
          return (
            <div
              key={idx}
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontSize: 12,
                padding: "6px 8px",
                background: "var(--bg-0)",
                borderRadius: "var(--r1)",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  color: "var(--text-1)",
                }}
              >
                {labelStr}
              </span>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontWeight: 600,
                }}
              >
                {s.value}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
