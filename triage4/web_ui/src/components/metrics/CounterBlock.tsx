import { priorityColor } from "../../util/priority";
import type { MetricFamily } from "../../types";

type Props = { family: MetricFamily };

export default function CounterBlock({ family }: Props) {
  const byLabel: Record<string, number> = {};
  for (const s of family.samples) {
    const label = s.labels["priority"] ?? s.labels["state"] ?? JSON.stringify(s.labels);
    byLabel[label] = (byLabel[label] ?? 0) + s.value;
  }
  const entries = Object.entries(byLabel).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((a, [, v]) => a + v, 0);

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
        counter
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
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {entries.map(([label, value]) => {
          const pct = total > 0 ? value / total : 0;
          const colour = priorityColor(label);
          return (
            <div key={label}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  fontSize: 12,
                  marginBottom: 2,
                }}
              >
                <span>{label}</span>
                <span
                  style={{ fontFamily: "var(--font-mono)", color: "var(--text-1)" }}
                >
                  {value}
                </span>
              </div>
              <div
                style={{
                  height: 4,
                  background: "var(--bg-0)",
                  borderRadius: 2,
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: `${pct * 100}%`,
                    height: "100%",
                    background: colour,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
