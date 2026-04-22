// Mission tab: fractal mission-level triage badge + 5-channel
// signature bars + reasons. Polls /mission/status every 10 s.

import { fetchMissionStatus } from "../api/endpoints";
import ConfidenceBar from "../components/casualties/ConfidenceBar";
import { usePolling } from "../hooks/usePolling";

const PRIO_COLOR: Record<string, string> = {
  escalate: "var(--prio-immediate)",
  sustain: "var(--prio-delayed)",
  wind_down: "var(--prio-minimal)",
};

const CHANNEL_LABELS: { key: keyof MissionSigKeys; label: string }[] = [
  { key: "casualty_density", label: "casualty density" },
  { key: "immediate_fraction", label: "immediate fraction" },
  { key: "unresolved_sector_fraction", label: "unresolved sectors" },
  { key: "medic_utilisation", label: "medic utilisation" },
  { key: "time_budget_burn", label: "time budget burn" },
];

type MissionSigKeys = {
  casualty_density: number;
  immediate_fraction: number;
  unresolved_sector_fraction: number;
  medic_utilisation: number;
  time_budget_burn: number;
};

export default function MissionPage() {
  const { data, error, loading, lastFetch, refresh } = usePolling(
    fetchMissionStatus,
    10_000,
  );

  return (
    <section style={{ maxWidth: 900, margin: "0 auto" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 16,
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Mission status</h1>
          <div
            style={{ color: "var(--text-2)", fontSize: 12, marginTop: 4 }}
          >
            Fractal K3-3.2 view: the mission itself triaged like a casualty.
          </div>
        </div>
        <button onClick={refresh} disabled={loading}>
          refresh
        </button>
      </header>

      {loading && !data && (
        <div style={{ color: "var(--text-2)", fontStyle: "italic" }}>
          loading mission status…
        </div>
      )}

      {error && (
        <div
          style={{
            padding: 12,
            border: "1px solid var(--err)",
            borderRadius: "var(--r2)",
            color: "var(--err)",
            marginBottom: 16,
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
              gridTemplateColumns: "1fr 1fr",
              gap: 16,
              marginBottom: 20,
            }}
          >
            <div
              style={{
                padding: 20,
                background: "var(--bg-1)",
                border: "1px solid var(--border-1)",
                borderLeft: `6px solid ${
                  PRIO_COLOR[data.priority] ?? "var(--prio-unknown)"
                }`,
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
                mission priority
              </div>
              <div
                style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color: PRIO_COLOR[data.priority] ?? "var(--text-0)",
                  textTransform: "uppercase",
                  marginTop: 4,
                }}
              >
                {data.priority.replace(/_/g, " ")}
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 13,
                  color: "var(--text-1)",
                  marginTop: 8,
                }}
              >
                fused score: {data.score.toFixed(3)}
              </div>
            </div>

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
                  marginBottom: 10,
                }}
              >
                reasons
              </div>
              {data.reasons.length === 0 ? (
                <div
                  style={{
                    color: "var(--text-2)",
                    fontStyle: "italic",
                    fontSize: 12,
                  }}
                >
                  no triage-elevating conditions active
                </div>
              ) : (
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: 18,
                    color: "var(--text-1)",
                    fontSize: 13,
                  }}
                >
                  {data.reasons.map((r, idx) => (
                    <li key={idx} style={{ marginBottom: 4 }}>
                      {r}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div
            style={{
              padding: 16,
              background: "var(--bg-1)",
              border: "1px solid var(--border-1)",
              borderRadius: "var(--r2)",
              marginBottom: 20,
            }}
          >
            <h3
              style={{
                margin: "0 0 12px",
                fontSize: 13,
                letterSpacing: 1,
                textTransform: "uppercase",
                color: "var(--text-2)",
              }}
            >
              signature channels
            </h3>
            {CHANNEL_LABELS.map(({ key, label }) => (
              <div key={key} style={{ marginBottom: 10 }}>
                <ConfidenceBar
                  label={label}
                  value={data.signature[key]}
                  color={
                    data.signature[key] > 0.7
                      ? "var(--prio-immediate)"
                      : data.signature[key] > 0.4
                        ? "var(--prio-delayed)"
                        : "var(--accent)"
                  }
                />
                <div
                  style={{
                    fontSize: 11,
                    color: "var(--text-2)",
                    fontFamily: "var(--font-mono)",
                    marginTop: 2,
                    display: "flex",
                    justifyContent: "space-between",
                  }}
                >
                  <span>channel weight contribution</span>
                  <span>{(data.contributions[key] ?? 0).toFixed(3)}</span>
                </div>
              </div>
            ))}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 12,
              fontSize: 12,
            }}
          >
            <div
              style={{
                padding: 12,
                background: "var(--bg-1)",
                border: "1px solid var(--border-1)",
                borderRadius: "var(--r2)",
              }}
            >
              <div
                style={{
                  color: "var(--text-2)",
                  textTransform: "uppercase",
                  letterSpacing: 1,
                  marginBottom: 6,
                }}
              >
                medic assignments
              </div>
              {Object.keys(data.medic_assignments).length === 0 ? (
                <div
                  style={{ fontStyle: "italic", color: "var(--text-2)" }}
                >
                  none
                </div>
              ) : (
                Object.entries(data.medic_assignments).map(([m, c]) => (
                  <div
                    key={m}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontFamily: "var(--font-mono)",
                      marginBottom: 2,
                    }}
                  >
                    <span>{m}</span>
                    <span style={{ color: "var(--accent)" }}>→ {c}</span>
                  </div>
                ))
              )}
            </div>

            <div
              style={{
                padding: 12,
                background: "var(--bg-1)",
                border: "1px solid var(--border-1)",
                borderRadius: "var(--r2)",
              }}
            >
              <div
                style={{
                  color: "var(--text-2)",
                  textTransform: "uppercase",
                  letterSpacing: 1,
                  marginBottom: 6,
                }}
              >
                unresolved regions
              </div>
              {data.unresolved_regions.length === 0 ? (
                <div
                  style={{ fontStyle: "italic", color: "var(--text-2)" }}
                >
                  none
                </div>
              ) : (
                data.unresolved_regions.map((r) => (
                  <div
                    key={r}
                    style={{
                      fontFamily: "var(--font-mono)",
                      marginBottom: 2,
                    }}
                  >
                    {r}
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}

      {lastFetch && (
        <div
          style={{
            marginTop: 12,
            fontSize: 10,
            color: "var(--text-2)",
            textAlign: "right",
            fontFamily: "var(--font-mono)",
          }}
        >
          last fetch: {new Date(lastFetch).toLocaleTimeString()}
        </div>
      )}
    </section>
  );
}
