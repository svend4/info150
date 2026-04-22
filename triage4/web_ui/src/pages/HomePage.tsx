// Home / executive summary: totals + mission status + top alerts.
// Polls /overview every 10 s.

import { fetchOverview } from "../api/endpoints";
import { usePolling } from "../hooks/usePolling";
import { priorityColor } from "../util/priority";
import { formatConfidence } from "../util/format";

const MISSION_COLOR: Record<string, string> = {
  escalate: "var(--prio-immediate)",
  sustain: "var(--prio-delayed)",
  wind_down: "var(--prio-minimal)",
};

export default function HomePage() {
  const { data, error, loading } = usePolling(fetchOverview, 10_000);

  return (
    <section style={{ maxWidth: 1100, margin: "0 auto" }}>
      <header style={{ marginBottom: 20 }}>
        <h1 style={{ margin: 0, fontSize: 24 }}>Overview</h1>
        <div
          style={{ color: "var(--text-2)", fontSize: 12, marginTop: 4 }}
        >
          Executive summary — totals, mission state, oldest unresponded
          immediate. Refreshes every 10 s.
        </div>
      </header>

      {loading && !data && (
        <div style={{ color: "var(--text-2)", fontStyle: "italic" }}>
          loading overview…
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
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 12,
              marginBottom: 20,
            }}
          >
            <BigStat label="casualties" value={String(data.total_casualties)} />
            <BigStat
              label="avg confidence"
              value={formatConfidence(data.avg_confidence)}
            />
            <BigStat
              label="medic assignments"
              value={String(data.n_medic_assignments)}
            />
            <BigStat
              label="unresolved regions"
              value={String(data.n_unresolved_regions)}
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
            <Panel title="priority distribution">
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "80px 1fr 40px",
                  gap: 8,
                  alignItems: "center",
                }}
              >
                {Object.entries(data.by_priority).map(([priority, count]) => {
                  const pct =
                    data.total_casualties > 0
                      ? count / data.total_casualties
                      : 0;
                  return [
                    <span
                      key={`l-${priority}`}
                      style={{
                        color: priorityColor(priority),
                        textTransform: "uppercase",
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    >
                      {priority}
                    </span>,
                    <div
                      key={`b-${priority}`}
                      style={{
                        height: 10,
                        background: "var(--bg-0)",
                        borderRadius: 3,
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          width: `${pct * 100}%`,
                          height: "100%",
                          background: priorityColor(priority),
                        }}
                      />
                    </div>,
                    <span
                      key={`c-${priority}`}
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 12,
                        color: "var(--text-1)",
                        textAlign: "right",
                      }}
                    >
                      {count}
                    </span>,
                  ];
                })}
              </div>
            </Panel>

            <Panel
              title="mission state"
              accent={MISSION_COLOR[data.mission_priority] ?? "var(--border-1)"}
            >
              <div
                style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color:
                    MISSION_COLOR[data.mission_priority] ?? "var(--text-0)",
                  textTransform: "uppercase",
                  marginBottom: 4,
                }}
              >
                {data.mission_priority.replace(/_/g, " ")}
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 13,
                  color: "var(--text-1)",
                  marginBottom: 10,
                }}
              >
                score {data.mission_score.toFixed(3)}
              </div>
              {data.mission_reasons.length === 0 ? (
                <div
                  style={{
                    color: "var(--text-2)",
                    fontStyle: "italic",
                    fontSize: 12,
                  }}
                >
                  no escalating conditions
                </div>
              ) : (
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: 18,
                    color: "var(--text-1)",
                    fontSize: 12,
                  }}
                >
                  {data.mission_reasons.map((r, idx) => (
                    <li key={idx}>{r}</li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>

          {data.oldest_unresponded_immediate && (
            <div
              style={{
                padding: 16,
                background: "var(--bg-1)",
                border: "1px solid var(--prio-immediate)",
                borderRadius: "var(--r2)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <div
                  style={{
                    color: "var(--prio-immediate)",
                    textTransform: "uppercase",
                    fontSize: 11,
                    letterSpacing: 1,
                    fontWeight: 600,
                  }}
                >
                  ⚠ oldest unresponded immediate
                </div>
                <div
                  style={{
                    fontSize: 24,
                    fontWeight: 700,
                    marginTop: 4,
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {data.oldest_unresponded_immediate}
                </div>
              </div>
              <div
                style={{
                  fontSize: 12,
                  color: "var(--text-1)",
                  maxWidth: 300,
                  textAlign: "right",
                }}
              >
                No medic has been assigned to this immediate-priority
                casualty yet. Jump to the Casualties tab to triage.
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function BigStat({ label, value }: { label: string; value: string }) {
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
          fontSize: 30,
          fontWeight: 700,
          fontFamily: "var(--font-mono)",
          marginTop: 6,
        }}
      >
        {value}
      </div>
    </div>
  );
}

function Panel({
  title,
  children,
  accent = "var(--border-1)",
}: {
  title: string;
  children: React.ReactNode;
  accent?: string;
}) {
  return (
    <div
      style={{
        padding: 16,
        background: "var(--bg-1)",
        border: "1px solid var(--border-1)",
        borderLeft: `4px solid ${accent}`,
        borderRadius: "var(--r2)",
      }}
    >
      <h3
        style={{
          margin: "0 0 12px",
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
