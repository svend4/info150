// Tasks tab: live-polled /tasks endpoint. Shows the recommended
// intervention queue produced by autonomy.TaskAllocator.

import { fetchTasks } from "../api/endpoints";
import { usePolling } from "../hooks/usePolling";
import { priorityColor } from "../util/priority";
import { downloadCsv, downloadJson } from "../util/export";
import { formatConfidence, formatCoord } from "../util/format";

export default function TasksPage() {
  const { data, error, loading, lastFetch, refresh } = usePolling(
    fetchTasks,
    10_000,
  );

  return (
    <section style={{ maxWidth: 840, margin: "0 auto" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 16,
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Recommended queue</h1>
          <div
            style={{ color: "var(--text-2)", fontSize: 12, marginTop: 4 }}
          >
            TaskAllocator ranks casualties by priority, then confidence,
            then freshness.
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() =>
              data &&
              downloadCsv(
                data.map((t, idx) => ({
                  rank: idx + 1,
                  casualty_id: t.casualty_id,
                  priority: t.priority,
                  confidence: t.confidence,
                  x: t.location.x,
                  y: t.location.y,
                })),
                "triage4_tasks.csv",
              )
            }
            disabled={!data || data.length === 0}
          >
            export CSV
          </button>
          <button
            onClick={() => data && downloadJson(data, "triage4_tasks.json")}
            disabled={!data || data.length === 0}
          >
            export JSON
          </button>
          <button onClick={refresh} disabled={loading}>
            refresh
          </button>
        </div>
      </header>

      {loading && !data && (
        <div style={{ color: "var(--text-2)", fontStyle: "italic" }}>
          loading queue…
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

      {data && data.length === 0 && (
        <div
          style={{
            padding: 24,
            textAlign: "center",
            color: "var(--text-2)",
            fontStyle: "italic",
            background: "var(--bg-1)",
            borderRadius: "var(--r2)",
          }}
        >
          the queue is empty
        </div>
      )}

      <ol
        style={{
          listStyle: "none",
          margin: 0,
          padding: 0,
          display: "grid",
          gap: 8,
        }}
      >
        {(data ?? []).map((t, idx) => (
          <li
            key={`${t.casualty_id}-${idx}`}
            style={{
              display: "grid",
              gridTemplateColumns: "40px 1fr 120px 120px 120px",
              alignItems: "center",
              gap: 12,
              padding: 12,
              background: "var(--bg-1)",
              border: "1px solid var(--border-1)",
              borderLeft: `4px solid ${priorityColor(t.priority)}`,
              borderRadius: "var(--r2)",
            }}
          >
            <div
              style={{
                fontFamily: "var(--font-mono)",
                color: "var(--text-2)",
              }}
            >
              #{idx + 1}
            </div>
            <div style={{ fontWeight: 600 }}>{t.casualty_id}</div>
            <div
              style={{
                color: priorityColor(t.priority),
                textTransform: "uppercase",
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              {t.priority}
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
              {formatConfidence(t.confidence)}
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                color: "var(--text-1)",
              }}
            >
              {formatCoord(t.location.x)}, {formatCoord(t.location.y)}
            </div>
          </li>
        ))}
      </ol>

      {lastFetch && (
        <div
          style={{
            marginTop: 10,
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
