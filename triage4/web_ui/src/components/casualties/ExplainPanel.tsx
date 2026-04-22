// Explain panel: priority + confidence + per-hypothesis breakdown.
// Data source: GET /casualties/{id}/explain.

import { useResource } from "../../hooks/useResource";
import { fetchExplanation } from "../../api/endpoints";
import { priorityColor } from "../../util/priority";
import { formatConfidence } from "../../util/format";
import ConfidenceBar from "./ConfidenceBar";

type Props = { casualtyId: string };

export default function ExplainPanel({ casualtyId }: Props) {
  const { data, error, loading } = useResource(
    (signal) => fetchExplanation(casualtyId, signal),
    [casualtyId],
  );

  if (loading && !data)
    return (
      <div style={{ padding: 16, color: "var(--text-2)" }}>
        loading explanation…
      </div>
    );
  if (error)
    return (
      <div style={{ padding: 16, color: "var(--err)" }}>
        failed to load explanation: {error.message}
      </div>
    );
  if (!data) return null;

  return (
    <section style={{ padding: 16 }}>
      <div style={{ marginBottom: 14 }}>
        <div style={{ color: "var(--text-2)", fontSize: 11, letterSpacing: 1, textTransform: "uppercase" }}>
          priority
        </div>
        <div
          style={{
            fontSize: 24,
            fontWeight: 700,
            color: priorityColor(data.priority),
            textTransform: "uppercase",
          }}
        >
          {data.priority}
        </div>
      </div>

      <ConfidenceBar label="overall confidence" value={data.confidence} />

      <h3 style={{ marginTop: 22, marginBottom: 10, fontSize: 13, letterSpacing: 1, textTransform: "uppercase", color: "var(--text-2)" }}>
        Hypotheses
      </h3>

      {data.top_hypotheses.length === 0 && (
        <div style={{ color: "var(--text-2)", fontStyle: "italic" }}>
          no hypotheses surfaced
        </div>
      )}

      {data.top_hypotheses.map((h, idx) => (
        <div
          key={idx}
          style={{
            marginBottom: 12,
            padding: 12,
            borderRadius: "var(--r2)",
            background: "var(--bg-1)",
            border: "1px solid var(--border-1)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: 6,
            }}
          >
            <strong>{h.kind}</strong>
            <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-1)" }}>
              {formatConfidence(h.score)}
            </span>
          </div>
          <ConfidenceBar label="score" value={h.score} showValue={false} />
          {h.why && (
            <div style={{ marginTop: 6, color: "var(--text-1)", fontSize: 12 }}>
              {h.why}
            </div>
          )}
        </div>
      ))}
    </section>
  );
}
