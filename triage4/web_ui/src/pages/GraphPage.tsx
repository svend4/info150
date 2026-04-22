// Graph tab: force-directed visualisation of the casualty graph.
// Edges are observation / support relations emitted by the backend.

import { fetchGraph } from "../api/endpoints";
import ForceGraph from "../components/graph/ForceGraph";
import { useResource } from "../hooks/useResource";
import { priorityColor } from "../util/priority";

export default function GraphPage() {
  const { data, error, loading, refresh } = useResource(fetchGraph);

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
          <h1 style={{ margin: 0, fontSize: 22 }}>Casualty graph</h1>
          <div style={{ color: "var(--text-2)", fontSize: 12, marginTop: 4 }}>
            Force-directed layout. Node colour = priority. Edges = tracked
            relations between casualties in the mission graph.
          </div>
        </div>
        <button onClick={refresh} disabled={loading}>
          refresh
        </button>
      </header>

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

      <div
        style={{
          background: "var(--bg-1)",
          borderRadius: "var(--r2)",
          border: "1px solid var(--border-1)",
          padding: 12,
        }}
      >
        {data ? (
          <>
            <ForceGraph data={data} />
            <div
              style={{
                marginTop: 10,
                fontSize: 11,
                color: "var(--text-2)",
                fontFamily: "var(--font-mono)",
              }}
            >
              {data.nodes.length} node{data.nodes.length === 1 ? "" : "s"}
              {" · "}
              {data.edges.length} edge{data.edges.length === 1 ? "" : "s"}
            </div>
          </>
        ) : (
          <div style={{ color: "var(--text-2)", fontStyle: "italic" }}>
            loading graph…
          </div>
        )}
      </div>

      <div
        style={{
          marginTop: 16,
          display: "flex",
          gap: 16,
          flexWrap: "wrap",
          fontSize: 12,
          color: "var(--text-1)",
        }}
      >
        {["immediate", "delayed", "minimal", "unknown"].map((p) => (
          <div
            key={p}
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: priorityColor(p),
              }}
            />
            <span>{p}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
