import { Fragment } from "react";

import type { MetricFamily } from "../../types";
import { summariseHistogram } from "../../api/metricsParser";

type Props = { family: MetricFamily };

export default function HistogramBlock({ family }: Props) {
  const { count, sum, avg, buckets } = summariseHistogram(family);
  // Incremental bucket counts (bucket[i] - bucket[i-1]) for the
  // per-bucket bars.
  const incremental: { label: string; count: number }[] = [];
  let prev = 0;
  for (const b of buckets) {
    const thisCount = Math.max(0, b.count - prev);
    incremental.push({
      label: b.le === "+Inf" ? "+∞" : `≤ ${b.le}`,
      count: thisCount,
    });
    prev = b.count;
  }
  const max = Math.max(1, ...incremental.map((i) => i.count));

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
        histogram
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

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 8,
          marginBottom: 14,
        }}
      >
        <Stat label="count" value={String(count)} />
        <Stat label="sum" value={sum.toFixed(3)} />
        <Stat label="avg" value={avg.toFixed(3)} />
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "80px 1fr 60px",
          gap: 6,
          alignItems: "center",
          fontSize: 11,
        }}
      >
        {incremental.map((b) => (
          <Fragment key={b.label}>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                color: "var(--text-1)",
                textAlign: "right",
              }}
            >
              {b.label}
            </span>
            <div
              style={{
                height: 10,
                background: "var(--bg-0)",
                borderRadius: 2,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${(b.count / max) * 100}%`,
                  height: "100%",
                  background: "var(--accent)",
                }}
              />
            </div>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                color: "var(--text-1)",
              }}
            >
              {b.count}
            </span>
          </Fragment>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        background: "var(--bg-0)",
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r1)",
        padding: 8,
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: "var(--text-2)",
          textTransform: "uppercase",
          letterSpacing: 1,
        }}
      >
        {label}
      </div>
      <div style={{ marginTop: 2, fontFamily: "var(--font-mono)", fontSize: 14 }}>
        {value}
      </div>
    </div>
  );
}
