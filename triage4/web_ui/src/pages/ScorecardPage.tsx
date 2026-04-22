// Scorecard tab: DARPA-gate KPI view + counterfactual regret.

import { fetchScorecard } from "../api/endpoints";
import Tooltip from "../components/common/Tooltip";
import { useResource } from "../hooks/useResource";
import { priorityColor } from "../util/priority";
import { formatPercent } from "../util/format";

export default function ScorecardPage() {
  const { data, error, loading, refresh } = useResource(fetchScorecard);

  return (
    <section style={{ maxWidth: 1100, margin: "0 auto" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 16,
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Evaluation scorecard</h1>
          <div
            style={{ color: "var(--text-2)", fontSize: 12, marginTop: 4 }}
          >
            DARPA Gate 2 rapid-triage accuracy + counterfactual regret.
            Ground truth comes from the demo seed's priority hints.
          </div>
        </div>
        <button onClick={refresh} disabled={loading}>
          refresh
        </button>
      </header>

      {loading && !data && (
        <div style={{ color: "var(--text-2)", fontStyle: "italic" }}>
          computing scorecard…
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
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 12,
              marginBottom: 20,
            }}
          >
            <Kpi
              label="accuracy"
              value={formatPercent(data.gate2.accuracy, 1)}
              good={data.gate2.accuracy >= 0.9}
            />
            <Kpi
              label={
                <Tooltip text="Macro-F1: the unweighted average of per-class F1 scores. Better than accuracy for imbalanced priority distributions — a 'high-accuracy' engine that only ever predicts the most common class gets a low macro-F1.">
                  macro F1
                </Tooltip>
              }
              value={data.gate2.macro_f1.toFixed(3)}
              good={data.gate2.macro_f1 >= 0.7}
            />
            <Kpi
              label={
                <Tooltip text="Critical miss rate: the fraction of truly-immediate casualties that the engine classified as delayed or minimal. In a triage context this is the headline safety metric — every other accuracy number is secondary.">
                  critical miss rate
                </Tooltip>
              }
              value={formatPercent(data.gate2.critical_miss_rate, 1)}
              good={data.gate2.critical_miss_rate === 0}
              invert
            />
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginBottom: 20,
            }}
          >
            <Section title="per-class (Gate 2)">
              <table
                style={{
                  width: "100%",
                  fontSize: 12,
                  borderCollapse: "collapse",
                  fontFamily: "var(--font-mono)",
                }}
              >
                <thead>
                  <tr style={{ color: "var(--text-2)", textAlign: "left" }}>
                    <th style={{ padding: 4 }}>class</th>
                    <th style={{ padding: 4 }}>P</th>
                    <th style={{ padding: 4 }}>R</th>
                    <th style={{ padding: 4 }}>F1</th>
                    <th style={{ padding: 4 }}>tp/fp/fn</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.gate2.per_class).map(([label, m]) => {
                    if (m.tp + m.fp + m.fn === 0) return null;
                    return (
                      <tr key={label}>
                        <td
                          style={{
                            padding: 4,
                            color: priorityColor(label),
                            textTransform: "uppercase",
                          }}
                        >
                          {label}
                        </td>
                        <td style={{ padding: 4 }}>{m.precision.toFixed(2)}</td>
                        <td style={{ padding: 4 }}>{m.recall.toFixed(2)}</td>
                        <td style={{ padding: 4 }}>{m.f1.toFixed(2)}</td>
                        <td
                          style={{
                            padding: 4,
                            color: "var(--text-1)",
                          }}
                        >
                          {m.tp}/{m.fp}/{m.fn}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Section>

            <Section title="confusion matrix">
              <ConfusionMatrix
                labels={data.gate2.class_labels}
                matrix={data.gate2.confusion_matrix}
              />
            </Section>
          </div>

          <Section title={`counterfactual regret (n = ${data.counterfactuals.n})`}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                marginBottom: 10,
              }}
            >
              <div>
                <div
                  style={{
                    color: "var(--text-2)",
                    fontSize: 11,
                    letterSpacing: 1,
                    textTransform: "uppercase",
                  }}
                >
                  mean regret
                </div>
                <div
                  style={{
                    fontSize: 28,
                    fontWeight: 700,
                    color:
                      data.counterfactuals.mean_regret === 0
                        ? "var(--ok)"
                        : data.counterfactuals.mean_regret < 0.1
                          ? "var(--warn)"
                          : "var(--err)",
                  }}
                >
                  {data.counterfactuals.mean_regret.toFixed(3)}
                </div>
              </div>
              <div
                style={{
                  fontSize: 11,
                  color: "var(--text-2)",
                  textAlign: "right",
                  maxWidth: 400,
                }}
              >
                Per-casualty regret = (best alternative outcome) − (actual).
                Zero = no better decision was available. Non-zero = a
                different priority would have produced a better outcome
                against the expected-outcome table.
              </div>
            </div>
            <table
              style={{
                width: "100%",
                fontSize: 12,
                borderCollapse: "collapse",
                fontFamily: "var(--font-mono)",
              }}
            >
              <thead>
                <tr style={{ color: "var(--text-2)", textAlign: "left" }}>
                  <th style={{ padding: 4 }}>id</th>
                  <th style={{ padding: 4 }}>severity</th>
                  <th style={{ padding: 4 }}>actual</th>
                  <th style={{ padding: 4 }}>outcome</th>
                  <th style={{ padding: 4 }}>best alt</th>
                  <th style={{ padding: 4 }}>regret</th>
                </tr>
              </thead>
              <tbody>
                {data.counterfactuals.cases.map((c) => (
                  <tr key={c.casualty_id}>
                    <td style={{ padding: 4 }}>{c.casualty_id}</td>
                    <td style={{ padding: 4 }}>{c.severity}</td>
                    <td
                      style={{
                        padding: 4,
                        color: priorityColor(c.actual_priority),
                        textTransform: "uppercase",
                      }}
                    >
                      {c.actual_priority}
                    </td>
                    <td style={{ padding: 4 }}>{c.actual_outcome.toFixed(2)}</td>
                    <td
                      style={{
                        padding: 4,
                        color: priorityColor(c.best_alternative),
                        textTransform: "uppercase",
                      }}
                    >
                      {c.best_alternative}
                    </td>
                    <td
                      style={{
                        padding: 4,
                        color:
                          c.regret === 0
                            ? "var(--ok)"
                            : c.regret < 0.1
                              ? "var(--warn)"
                              : "var(--err)",
                      }}
                    >
                      {c.regret.toFixed(3)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>
        </>
      )}
    </section>
  );
}

function Kpi({
  label,
  value,
  good,
  invert = false,
}: {
  label: React.ReactNode;
  value: string;
  good: boolean;
  invert?: boolean;
}) {
  const color = good
    ? invert
      ? "var(--ok)"
      : "var(--ok)"
    : "var(--warn)";
  return (
    <div
      style={{
        padding: 16,
        background: "var(--bg-1)",
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r2)",
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
        {label}
      </div>
      <div
        style={{
          fontSize: 28,
          fontWeight: 700,
          color,
          fontFamily: "var(--font-mono)",
          marginTop: 4,
        }}
      >
        {value}
      </div>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        padding: 14,
        background: "var(--bg-1)",
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r2)",
        marginBottom: 12,
      }}
    >
      <h3
        style={{
          margin: "0 0 10px",
          fontSize: 13,
          textTransform: "uppercase",
          letterSpacing: 1,
          color: "var(--text-2)",
        }}
      >
        {title}
      </h3>
      {children}
    </div>
  );
}

function ConfusionMatrix({
  labels,
  matrix,
}: {
  labels: string[];
  matrix: number[][];
}) {
  // Hide completely-empty rows/columns for readability.
  const activeIdx = labels
    .map((_, i) =>
      matrix[i]?.some((v) => v > 0) ||
      matrix.some((row) => (row[i] ?? 0) > 0)
        ? i
        : -1,
    )
    .filter((i) => i >= 0);
  return (
    <table
      style={{
        width: "100%",
        fontSize: 11,
        borderCollapse: "collapse",
        fontFamily: "var(--font-mono)",
      }}
    >
      <thead>
        <tr>
          <th style={{ padding: 4, color: "var(--text-2)" }}>actual ↓ / pred →</th>
          {activeIdx.map((i) => (
            <th
              key={i}
              style={{
                padding: 4,
                color: priorityColor(labels[i]),
                textTransform: "uppercase",
              }}
            >
              {labels[i]}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {activeIdx.map((i) => (
          <tr key={i}>
            <td
              style={{
                padding: 4,
                color: priorityColor(labels[i]),
                textTransform: "uppercase",
              }}
            >
              {labels[i]}
            </td>
            {activeIdx.map((j) => (
              <td
                key={j}
                style={{
                  padding: 4,
                  textAlign: "center",
                  color: i === j ? "var(--ok)" : "var(--text-0)",
                  background: i === j ? "var(--bg-2)" : "transparent",
                }}
              >
                {matrix[i][j]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
