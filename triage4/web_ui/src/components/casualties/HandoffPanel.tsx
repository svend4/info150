// Handoff panel: compact medic-facing payload + copy-to-clipboard.
// Data source: GET /casualties/{id}/handoff.

import { useState } from "react";

import { useResource } from "../../hooks/useResource";
import { fetchHandoff } from "../../api/endpoints";
import { priorityColor } from "../../util/priority";
import { formatConfidence, formatCoord } from "../../util/format";
import MarkerSection from "./MarkerSection";

type Props = { casualtyId: string };

export default function HandoffPanel({ casualtyId }: Props) {
  const { data, error, loading } = useResource(
    (signal) => fetchHandoff(casualtyId, signal),
    [casualtyId],
  );
  const [copied, setCopied] = useState(false);

  if (loading && !data)
    return (
      <div style={{ padding: 16, color: "var(--text-2)" }}>
        loading handoff payload…
      </div>
    );
  if (error)
    return (
      <div style={{ padding: 16, color: "var(--err)" }}>
        failed: {error.message}
      </div>
    );
  if (!data) return null;

  const jsonText = JSON.stringify(data, null, 2);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(jsonText);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard not available (e.g. insecure context) — no-op */
    }
  };

  return (
    <section style={{ padding: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 14,
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
            recommended action
          </div>
          <div style={{ fontSize: 16, fontWeight: 600, marginTop: 2 }}>
            {data.recommended_action}
          </div>
        </div>
        <div
          style={{
            color: priorityColor(data.priority),
            textTransform: "uppercase",
            fontSize: 18,
            fontWeight: 700,
          }}
        >
          {data.priority}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <Stat label="id" value={data.casualty_id} mono />
        <Stat label="confidence" value={formatConfidence(data.confidence)} mono />
        <Stat
          label="location"
          value={`${formatCoord(data.location.x)}, ${formatCoord(data.location.y)}`}
          mono
        />
      </div>

      <h3
        style={{
          fontSize: 13,
          textTransform: "uppercase",
          letterSpacing: 1,
          color: "var(--text-2)",
          marginTop: 18,
          marginBottom: 10,
        }}
      >
        top hypotheses
      </h3>
      {data.top_hypotheses.map((h, idx) => (
        <div
          key={idx}
          style={{
            padding: 10,
            marginBottom: 8,
            borderRadius: "var(--r1)",
            background: "var(--bg-1)",
            border: "1px solid var(--border-1)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <strong>{h.kind}</strong>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                color: "var(--text-1)",
              }}
            >
              {formatConfidence(h.score)}
            </span>
          </div>
          {h.explanation && (
            <div
              style={{
                marginTop: 4,
                fontSize: 12,
                color: "var(--text-1)",
              }}
            >
              {h.explanation}
            </div>
          )}
        </div>
      ))}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 18,
          marginBottom: 6,
        }}
      >
        <h3
          style={{
            fontSize: 13,
            textTransform: "uppercase",
            letterSpacing: 1,
            color: "var(--text-2)",
            margin: 0,
          }}
        >
          raw payload
        </h3>
        <button onClick={onCopy}>
          {copied ? "copied ✓" : "copy JSON"}
        </button>
      </div>
      <pre style={{ fontSize: 11, maxHeight: 300 }}>{jsonText}</pre>

      <MarkerSection casualtyId={casualtyId} />
    </section>
  );
}

function Stat({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div
        style={{
          color: "var(--text-2)",
          fontSize: 11,
          letterSpacing: 1,
          textTransform: "uppercase",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 14,
          fontFamily: mono ? "var(--font-mono)" : "inherit",
        }}
      >
        {value}
      </div>
    </div>
  );
}
