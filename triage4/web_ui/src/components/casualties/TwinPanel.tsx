// Twin panel: Bayesian patient twin posterior for a casualty.
// Data source: GET /casualties/{id}/twin.

import { fetchCasualtyTwin } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import { priorityColor } from "../../util/priority";
import { formatPercent } from "../../util/format";
import ConfidenceBar from "./ConfidenceBar";

type Props = { casualtyId: string };

const PRIORITY_ORDER = ["immediate", "delayed", "minimal"];

export default function TwinPanel({ casualtyId }: Props) {
  const { data, error, loading } = useResource(
    (signal) => fetchCasualtyTwin(casualtyId, signal),
    [casualtyId],
  );

  if (loading && !data)
    return (
      <div style={{ padding: 16, color: "var(--text-2)" }}>
        running 200-particle filter…
      </div>
    );
  if (error)
    return (
      <div style={{ padding: 16, color: "var(--err)" }}>
        {error.message}
      </div>
    );
  if (!data) return null;

  return (
    <section style={{ padding: 16 }}>
      <div
        style={{
          color: "var(--text-2)",
          fontSize: 11,
          letterSpacing: 1,
          textTransform: "uppercase",
        }}
      >
        most likely priority
      </div>
      <div
        style={{
          fontSize: 28,
          fontWeight: 700,
          color: priorityColor(data.most_likely_priority),
          textTransform: "uppercase",
          marginTop: 2,
        }}
      >
        {data.most_likely_priority}
        <span
          style={{
            fontSize: 14,
            color: "var(--text-1)",
            fontWeight: 400,
            marginLeft: 12,
            fontFamily: "var(--font-mono)",
          }}
        >
          {formatPercent(data.most_likely_probability, 1)}
        </span>
      </div>

      <h3
        style={{
          marginTop: 22,
          marginBottom: 10,
          fontSize: 13,
          textTransform: "uppercase",
          letterSpacing: 1,
          color: "var(--text-2)",
        }}
      >
        posterior distribution
      </h3>

      {PRIORITY_ORDER.map((p) => (
        <div key={p} style={{ marginBottom: 8 }}>
          <ConfidenceBar
            label={p}
            value={data.priority_probs[p] ?? 0}
            color={priorityColor(p)}
          />
        </div>
      ))}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 10,
          marginTop: 16,
        }}
      >
        <div
          style={{
            padding: 10,
            background: "var(--bg-1)",
            border: "1px solid var(--border-1)",
            borderRadius: "var(--r1)",
          }}
        >
          <div
            style={{
              fontSize: 11,
              color: "var(--text-2)",
              letterSpacing: 1,
              textTransform: "uppercase",
            }}
          >
            deterioration rate
          </div>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 16,
              marginTop: 2,
            }}
          >
            {data.deterioration_rate.toFixed(3)}
          </div>
        </div>

        <div
          style={{
            padding: 10,
            background: "var(--bg-1)",
            border: "1px solid var(--border-1)",
            borderRadius: "var(--r1)",
          }}
        >
          <div
            style={{
              fontSize: 11,
              color: "var(--text-2)",
              letterSpacing: 1,
              textTransform: "uppercase",
            }}
          >
            effective sample size
          </div>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 16,
              marginTop: 2,
              color: data.is_degenerate ? "var(--warn)" : "var(--text-0)",
            }}
          >
            {data.effective_sample_size.toFixed(1)} / 200
          </div>
        </div>
      </div>

      {data.is_degenerate && (
        <div
          style={{
            marginTop: 12,
            padding: 10,
            borderRadius: "var(--r1)",
            background: "var(--bg-1)",
            border: "1px solid var(--warn)",
            color: "var(--warn)",
            fontSize: 12,
          }}
        >
          ⚠ Particle cloud degenerate (ESS &lt; 5). The posterior estimate
          is untrustworthy — more observations needed before acting on it.
        </div>
      )}
    </section>
  );
}
