// Uncertainty panel: per-channel quality + overall confidence +
// base vs adjusted score side-by-side.

import { fetchUncertainty } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import { formatPercent } from "../../util/format";
import ConfidenceBar from "./ConfidenceBar";

type Props = { casualtyId: string };

const CHANNEL_COLORS: Record<string, string> = {
  breathing_quality: "var(--accent)",
  perfusion_quality: "var(--prio-delayed)",
  bleeding_confidence: "var(--prio-immediate)",
  thermal_quality: "var(--prio-expectant)",
};

export default function UncertaintyPanel({ casualtyId }: Props) {
  const { data, error, loading } = useResource(
    (signal) => fetchUncertainty(casualtyId, signal),
    [casualtyId],
  );

  if (loading && !data)
    return (
      <div style={{ padding: 16, color: "var(--text-2)" }}>
        propagating uncertainty…
      </div>
    );
  if (error)
    return (
      <div style={{ padding: 16, color: "var(--err)" }}>{error.message}</div>
    );
  if (!data) return null;

  const perChannel = Object.entries(data.per_channel_confidence);

  return (
    <section style={{ padding: 16 }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 10,
          marginBottom: 18,
        }}
      >
        <Stat
          label="base score"
          value={data.base_score.toFixed(3)}
        />
        <Stat
          label="adjusted score"
          value={data.adjusted_score.toFixed(3)}
          accent
        />
      </div>

      <h3
        style={{
          margin: "0 0 10px",
          fontSize: 13,
          letterSpacing: 1,
          textTransform: "uppercase",
          color: "var(--text-2)",
        }}
      >
        overall confidence
      </h3>
      <ConfidenceBar
        label="confidence"
        value={data.overall_confidence}
      />
      <div
        style={{
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          color: "var(--text-2)",
          marginTop: -2,
          textAlign: "right",
        }}
      >
        uncertainty = {formatPercent(data.overall_uncertainty, 0)}
      </div>

      <h3
        style={{
          margin: "18px 0 10px",
          fontSize: 13,
          letterSpacing: 1,
          textTransform: "uppercase",
          color: "var(--text-2)",
        }}
      >
        per-channel quality
      </h3>
      {perChannel.length === 0 && (
        <div
          style={{
            color: "var(--text-2)",
            fontStyle: "italic",
            fontSize: 12,
          }}
        >
          no per-channel quality flags were attached to this signature
        </div>
      )}
      {perChannel.map(([channel, value]) => (
        <ConfidenceBar
          key={channel}
          label={channel.replace(/_/g, " ")}
          value={value}
          color={CHANNEL_COLORS[channel] ?? "var(--accent)"}
        />
      ))}

      <div
        style={{
          marginTop: 16,
          padding: 10,
          background: "var(--bg-1)",
          border: "1px solid var(--border-1)",
          borderRadius: "var(--r1)",
          fontSize: 12,
          color: "var(--text-1)",
        }}
      >
        Adjusted score = base score × overall confidence. When sensor
        quality drops, the engine de-prioritises low-trust channels
        rather than acting on them at face value.
      </div>
    </section>
  );
}

function Stat({
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
        padding: 12,
        background: "var(--bg-1)",
        border: `1px solid ${accent ? "var(--accent-dim)" : "var(--border-1)"}`,
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
          fontSize: 22,
          fontWeight: 700,
          fontFamily: "var(--font-mono)",
          color: accent ? "var(--accent)" : "var(--text-0)",
          marginTop: 4,
        }}
      >
        {value}
      </div>
    </div>
  );
}
