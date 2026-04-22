// Conflict panel: raw hypothesis scores from the BodyStateGraph →
// ConflictResolver-adjusted ranking + conflict group winners.

import { fetchConflict } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import { formatScore } from "../../util/format";
import ConfidenceBar from "./ConfidenceBar";

type Props = { casualtyId: string };

export default function ConflictPanel({ casualtyId }: Props) {
  const { data, error, loading } = useResource(
    (signal) => fetchConflict(casualtyId, signal),
    [casualtyId],
  );

  if (loading && !data)
    return (
      <div style={{ padding: 16, color: "var(--text-2)" }}>
        reconciling hypotheses…
      </div>
    );
  if (error)
    return (
      <div style={{ padding: 16, color: "var(--err)" }}>{error.message}</div>
    );
  if (!data) return null;

  return (
    <section style={{ padding: 16 }}>
      {data.evidence_tokens.length > 0 && (
        <>
          <h3
            style={{
              margin: "0 0 10px",
              fontSize: 13,
              letterSpacing: 1,
              textTransform: "uppercase",
              color: "var(--text-2)",
            }}
          >
            evidence tokens
          </h3>
          <div
            style={{
              display: "grid",
              gap: 6,
              marginBottom: 18,
            }}
          >
            {data.evidence_tokens.map((t, idx) => (
              <div
                key={idx}
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 60px",
                  gap: 10,
                  padding: 8,
                  background: "var(--bg-1)",
                  border: "1px solid var(--border-1)",
                  borderRadius: "var(--r1)",
                  fontSize: 12,
                }}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>{t.name}</div>
                  <div style={{ fontSize: 11, color: "var(--text-2)" }}>
                    {t.source} — {t.note}
                  </div>
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    color: "var(--accent)",
                    textAlign: "right",
                    alignSelf: "center",
                  }}
                >
                  {formatScore(t.strength)}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <h3
        style={{
          margin: "0 0 10px",
          fontSize: 13,
          letterSpacing: 1,
          textTransform: "uppercase",
          color: "var(--text-2)",
        }}
      >
        reconciled ranking
      </h3>

      {data.ranked.length === 0 && (
        <div
          style={{
            fontStyle: "italic",
            color: "var(--text-2)",
            fontSize: 12,
            marginBottom: 16,
          }}
        >
          no hypotheses crossed the activation threshold
        </div>
      )}

      <div style={{ display: "grid", gap: 8, marginBottom: 18 }}>
        {data.ranked.map((r) => (
          <div
            key={r.name}
            style={{
              padding: 10,
              background: r.suppressed ? "var(--bg-0)" : "var(--bg-1)",
              border: `1px solid ${
                r.suppressed ? "var(--border-1)" : "var(--border-2)"
              }`,
              borderRadius: "var(--r2)",
              opacity: r.suppressed ? 0.5 : 1,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
              }}
            >
              <span
                style={{
                  fontWeight: 600,
                  textDecoration: r.suppressed ? "line-through" : "none",
                }}
              >
                {r.name}
              </span>
              <span
                style={{
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  color: "var(--text-1)",
                }}
              >
                raw {formatScore(r.raw_score)} · adj {formatScore(r.adjusted_score)}
              </span>
            </div>
            <ConfidenceBar
              label=""
              value={r.adjusted_score}
              showValue={false}
              color={
                r.adjusted_score > r.raw_score
                  ? "var(--ok)"
                  : r.adjusted_score < r.raw_score
                    ? "var(--warn)"
                    : "var(--accent)"
              }
            />
            {r.reasons.length > 0 && (
              <ul
                style={{
                  margin: "6px 0 0",
                  paddingLeft: 18,
                  fontSize: 11,
                  color: "var(--text-2)",
                }}
              >
                {r.reasons.map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>

      {data.groups.length > 0 && (
        <>
          <h3
            style={{
              margin: "0 0 10px",
              fontSize: 13,
              letterSpacing: 1,
              textTransform: "uppercase",
              color: "var(--text-2)",
            }}
          >
            conflict groups
          </h3>
          <div style={{ display: "grid", gap: 6 }}>
            {data.groups.map((g, idx) => (
              <div
                key={idx}
                style={{
                  padding: 10,
                  background: "var(--bg-1)",
                  border: "1px solid var(--border-1)",
                  borderRadius: "var(--r1)",
                  fontSize: 12,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 4,
                  }}
                >
                  <span style={{ color: "var(--text-2)" }}>
                    members: {g.members.join(", ")}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      color: "var(--text-1)",
                    }}
                  >
                    winner score {formatScore(g.winner_score)}
                  </span>
                </div>
                <div style={{ color: "var(--ok)", fontWeight: 600 }}>
                  winner: {g.winner ?? "—"}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
