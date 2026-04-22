// Second-opinion panel: 3 independent classifiers (RapidTriage,
// Larrey baseline, C.elegans network) run against the same
// signature. Disagreement is flagged.

import { fetchSecondOpinion } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import { priorityColor } from "../../util/priority";

type Props = { casualtyId: string };

export default function SecondOpinionPanel({ casualtyId }: Props) {
  const { data, error, loading } = useResource(
    (signal) => fetchSecondOpinion(casualtyId, signal),
    [casualtyId],
  );

  if (loading && !data)
    return (
      <div style={{ padding: 16, color: "var(--text-2)" }}>
        running classifiers…
      </div>
    );
  if (error)
    return (
      <div style={{ padding: 16, color: "var(--err)" }}>{error.message}</div>
    );
  if (!data) return null;

  return (
    <section style={{ padding: 16 }}>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          marginBottom: 14,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 11,
              color: "var(--text-2)",
              letterSpacing: 1,
              textTransform: "uppercase",
            }}
          >
            cross-check
          </div>
          <div
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: data.agreement ? "var(--ok)" : "var(--warn)",
              marginTop: 2,
            }}
          >
            {data.agreement
              ? "all classifiers agree"
              : `${data.distinct_priorities.length} distinct priorities`}
          </div>
        </div>
        {!data.agreement && (
          <div
            style={{
              padding: "6px 10px",
              background: "var(--bg-1)",
              border: "1px solid var(--warn)",
              borderRadius: "var(--r1)",
              fontSize: 11,
              color: "var(--warn)",
              maxWidth: 280,
            }}
          >
            ⚠ Independent classifiers disagree — operator judgement
            recommended before acting.
          </div>
        )}
      </div>

      <div style={{ display: "grid", gap: 10 }}>
        {data.classifiers.map((c) => (
          <div
            key={c.name}
            style={{
              padding: 12,
              background: "var(--bg-1)",
              border: "1px solid var(--border-1)",
              borderLeft: `4px solid ${priorityColor(c.priority)}`,
              borderRadius: "var(--r2)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                marginBottom: 4,
              }}
            >
              <strong>{c.name}</strong>
              <span
                style={{
                  color: priorityColor(c.priority),
                  textTransform: "uppercase",
                  fontSize: 12,
                  fontWeight: 700,
                }}
              >
                {c.priority}
                {c.score !== null && (
                  <span
                    style={{
                      color: "var(--text-1)",
                      marginLeft: 6,
                      fontFamily: "var(--font-mono)",
                      fontWeight: 400,
                    }}
                  >
                    {c.score.toFixed(2)}
                  </span>
                )}
              </span>
            </div>
            <div
              style={{
                fontSize: 12,
                color: "var(--text-2)",
                marginBottom: 6,
              }}
            >
              {c.description}
            </div>
            {c.reasons.length > 0 && (
              <ul
                style={{
                  margin: 0,
                  paddingLeft: 18,
                  fontSize: 12,
                  color: "var(--text-1)",
                }}
              >
                {c.reasons.map((r, idx) => (
                  <li key={idx} style={{ marginBottom: 2 }}>
                    {r}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
