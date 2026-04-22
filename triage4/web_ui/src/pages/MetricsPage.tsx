// Metrics tab: polls /metrics (Prometheus text) every 5 s, parses
// it client-side, renders one block per family. Counter / histogram
// / gauge each have their own viz.

import { useMemo } from "react";

import { fetchMetricsText } from "../api/endpoints";
import { parseMetrics } from "../api/metricsParser";
import CounterBlock from "../components/metrics/CounterBlock";
import GaugeBlock from "../components/metrics/GaugeBlock";
import HistogramBlock from "../components/metrics/HistogramBlock";
import { usePolling } from "../hooks/usePolling";
import { formatAge } from "../util/format";

export default function MetricsPage() {
  const { data, error, loading, lastFetch, refresh } = usePolling(
    fetchMetricsText,
    5_000,
  );
  const parsed = useMemo(
    () => (data ? parseMetrics(data) : null),
    [data],
  );

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
          <h1 style={{ margin: 0, fontSize: 22 }}>Metrics</h1>
          <div style={{ color: "var(--text-2)", fontSize: 12, marginTop: 4 }}>
            Prometheus text-exposition parsed client-side. Polled every 5 s.
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span
            style={{
              fontSize: 11,
              color: "var(--text-2)",
              fontFamily: "var(--font-mono)",
            }}
          >
            last fetch: {formatAge(lastFetch)}
          </span>
          <button onClick={refresh} disabled={loading}>
            refresh
          </button>
        </div>
      </header>

      {loading && !parsed && (
        <div style={{ color: "var(--text-2)", fontStyle: "italic" }}>
          loading metrics…
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

      {parsed && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
            gap: 12,
          }}
        >
          {parsed.families.map((fam) => {
            if (fam.type === "counter") return <CounterBlock key={fam.name} family={fam} />;
            if (fam.type === "histogram") return <HistogramBlock key={fam.name} family={fam} />;
            return <GaugeBlock key={fam.name} family={fam} />;
          })}
        </div>
      )}
    </section>
  );
}
