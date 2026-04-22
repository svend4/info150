// Sensing tab: active-sensing planner recommendations. Ranks
// casualties by expected info gain = uncertainty × priority_weight
// × novelty. Top one is the autonomy layer's next-observation
// target.

import { fetchSensingRanked } from "../api/endpoints";
import ConfidenceBar from "../components/casualties/ConfidenceBar";
import Tooltip from "../components/common/Tooltip";
import { usePolling } from "../hooks/usePolling";
import { formatScore } from "../util/format";

export default function SensingPage() {
  const { data, error, loading, refresh } = usePolling(
    () => fetchSensingRanked(10),
    15_000,
  );

  return (
    <section style={{ maxWidth: 1000, margin: "0 auto" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 16,
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Active sensing</h1>
          <div
            style={{ color: "var(--text-2)", fontSize: 12, marginTop: 4 }}
          >
            Next observation target chosen by expected{" "}
            <Tooltip text="Expected information gain = uncertainty × priority_weight × novelty. High when the casualty is uncertain, high-priority, and has rarely been re-observed. Drives the autonomy layer's revisit queue.">
              info gain
            </Tooltip>{" "}
            over the current casualty graph.
          </div>
        </div>
        <button onClick={refresh} disabled={loading}>
          refresh
        </button>
      </header>

      {loading && !data && (
        <div style={{ color: "var(--text-2)", fontStyle: "italic" }}>
          ranking targets…
        </div>
      )}

      {error && (
        <div
          style={{
            padding: 12,
            border: "1px solid var(--err)",
            borderRadius: "var(--r2)",
            color: "var(--err)",
          }}
        >
          {error.message}
        </div>
      )}

      {data && (
        <>
          {data.top_recommendation && (
            <div
              style={{
                padding: 16,
                background: "var(--bg-1)",
                border: "1px solid var(--accent)",
                borderLeft: "6px solid var(--accent)",
                borderRadius: "var(--r2)",
                marginBottom: 20,
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  color: "var(--text-2)",
                  letterSpacing: 1,
                  textTransform: "uppercase",
                  marginBottom: 4,
                }}
              >
                next observation target
              </div>
              <div
                style={{
                  fontSize: 28,
                  fontWeight: 700,
                  color: "var(--accent)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {data.top_recommendation.casualty_id}
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(4, 1fr)",
                  gap: 10,
                  marginTop: 10,
                  fontSize: 12,
                }}
              >
                <MiniStat
                  label="info gain"
                  value={formatScore(data.top_recommendation.expected_info_gain)}
                  accent
                />
                <MiniStat
                  label="uncertainty"
                  value={formatScore(data.top_recommendation.uncertainty)}
                />
                <MiniStat
                  label="priority wt"
                  value={formatScore(data.top_recommendation.priority_weight)}
                />
                <MiniStat
                  label="novelty"
                  value={formatScore(data.top_recommendation.novelty)}
                />
              </div>
              {data.top_recommendation.reasons.length > 0 && (
                <ul
                  style={{
                    margin: "10px 0 0",
                    paddingLeft: 18,
                    fontSize: 12,
                    color: "var(--text-1)",
                  }}
                >
                  {data.top_recommendation.reasons.map((r, idx) => (
                    <li key={idx}>{r}</li>
                  ))}
                </ul>
              )}
            </div>
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
            ranking (top {data.recommendations.length})
          </h3>

          <div style={{ display: "grid", gap: 8 }}>
            {data.recommendations.map((r, idx) => (
              <div
                key={r.casualty_id}
                style={{
                  display: "grid",
                  gridTemplateColumns: "32px 1fr 2fr 60px",
                  gap: 12,
                  alignItems: "center",
                  padding: 10,
                  background: "var(--bg-1)",
                  border: "1px solid var(--border-1)",
                  borderRadius: "var(--r2)",
                }}
              >
                <div
                  style={{
                    color: "var(--text-2)",
                    fontFamily: "var(--font-mono)",
                    textAlign: "right",
                  }}
                >
                  #{idx + 1}
                </div>
                <div style={{ fontWeight: 600, fontFamily: "var(--font-mono)" }}>
                  {r.casualty_id}
                </div>
                <div>
                  <ConfidenceBar
                    label={`info gain — unc ${r.uncertainty.toFixed(2)} · wt ${r.priority_weight.toFixed(2)} · nov ${r.novelty.toFixed(2)}`}
                    value={Math.min(1.0, r.expected_info_gain * 3)}
                    showValue={false}
                    color="var(--accent)"
                  />
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    textAlign: "right",
                    color:
                      r.expected_info_gain > 0.3
                        ? "var(--accent)"
                        : "var(--text-1)",
                  }}
                >
                  {formatScore(r.expected_info_gain)}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function MiniStat({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div
      style={{
        padding: 8,
        background: "var(--bg-0)",
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r1)",
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: "var(--text-2)",
          letterSpacing: 1,
          textTransform: "uppercase",
        }}
      >
        {label}
      </div>
      <div
        style={{
          marginTop: 2,
          fontSize: 16,
          fontWeight: 600,
          fontFamily: "var(--font-mono)",
          color: accent ? "var(--accent)" : "var(--text-0)",
        }}
      >
        {value}
      </div>
    </div>
  );
}
