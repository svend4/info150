// Default tab of CasualtyDetail: core signature + location card.

import type { Casualty } from "../../types";
import { priorityColor } from "../../util/priority";
import { formatConfidence, formatCoord, formatScore } from "../../util/format";
import ConfidenceBar from "./ConfidenceBar";

type Props = { casualty: Casualty };

export default function CasualtyOverview({ casualty }: Props) {
  const sig = casualty.signatures;
  return (
    <section style={{ padding: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 20,
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
            casualty
          </div>
          <h1 style={{ margin: "2px 0 0", fontSize: 28, fontWeight: 700 }}>
            {casualty.id}
          </h1>
        </div>
        <div
          style={{
            textAlign: "right",
            color: priorityColor(casualty.triage_priority),
            fontSize: 22,
            fontWeight: 700,
            textTransform: "uppercase",
          }}
        >
          {casualty.triage_priority}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
          gap: 12,
          marginBottom: 20,
        }}
      >
        <Stat label="confidence" value={formatConfidence(casualty.confidence)} />
        <Stat
          label="location"
          value={`${formatCoord(casualty.location.x)}, ${formatCoord(casualty.location.y)}`}
        />
        <Stat label="status" value={casualty.status} />
        <Stat label="platform" value={casualty.platform_source} />
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
        signatures
      </h3>

      <ConfidenceBar
        label="bleeding visual"
        value={sig.bleeding_visual_score}
        color="var(--prio-immediate)"
      />
      <ConfidenceBar
        label="perfusion drop"
        value={sig.perfusion_drop_score}
        color="var(--prio-delayed)"
      />
      <ConfidenceBar
        label="chest motion"
        value={Math.max(0, Math.min(1, sig.chest_motion_fd))}
        color="var(--accent)"
      />
      {sig.posture_instability_score !== undefined && (
        <ConfidenceBar
          label="posture instability"
          value={sig.posture_instability_score}
          color="var(--prio-expectant)"
        />
      )}
      {sig.thermal_asymmetry_score !== undefined && (
        <ConfidenceBar
          label="thermal asymmetry"
          value={sig.thermal_asymmetry_score}
          color="var(--prio-delayed)"
        />
      )}

      {casualty.hypotheses.length > 0 && (
        <>
          <h3
            style={{
              fontSize: 13,
              textTransform: "uppercase",
              letterSpacing: 1,
              color: "var(--text-2)",
              marginTop: 22,
              marginBottom: 10,
            }}
          >
            hypotheses (raw)
          </h3>
          <div style={{ display: "grid", gap: 6 }}>
            {casualty.hypotheses.map((h, idx) => (
              <div
                key={idx}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  padding: "8px 10px",
                  background: "var(--bg-1)",
                  borderRadius: "var(--r1)",
                  border: "1px solid var(--border-1)",
                }}
              >
                <span>{h.kind}</span>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    color: "var(--text-1)",
                  }}
                >
                  {formatScore(h.score)}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        padding: 10,
        background: "var(--bg-1)",
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r2)",
      }}
    >
      <div
        style={{
          fontSize: 11,
          letterSpacing: 1,
          textTransform: "uppercase",
          color: "var(--text-2)",
        }}
      >
        {label}
      </div>
      <div style={{ marginTop: 4, fontFamily: "var(--font-mono)" }}>{value}</div>
    </div>
  );
}
