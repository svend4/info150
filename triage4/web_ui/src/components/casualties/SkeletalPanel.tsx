// Skeletal panel: 13-joint humanoid stick-figure with wound-
// intensity colouring + mirror-pair asymmetry bars + per-joint
// trend table.

import { useMemo } from "react";

import { fetchSkeletal } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";
import type { JointTrend } from "../../types";
import { formatScore } from "../../util/format";
import ConfidenceBar from "./ConfidenceBar";

type Props = { casualtyId: string };

function woundColor(intensity: number): string {
  // 0 = grey, 1 = red
  if (intensity <= 0) return "var(--text-2)";
  if (intensity < 0.3) return "#7aa45f";
  if (intensity < 0.6) return "#d89d4a";
  return "var(--prio-immediate)";
}

export default function SkeletalPanel({ casualtyId }: Props) {
  const { data, error, loading } = useResource(
    (signal) => fetchSkeletal(casualtyId, signal),
    [casualtyId],
  );

  const scaled = useMemo(() => {
    if (!data?.latest) return null;
    // Fit all joint coords into an 80×100 stick-figure canvas.
    const positions = Object.values(data.latest.joints);
    const xs = positions.map(([x]) => x);
    const ys = positions.map(([, y]) => y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const spanX = Math.max(0.01, maxX - minX);
    const spanY = Math.max(0.01, maxY - minY);

    const pad = 10;
    const w = 80;
    const h = 120;
    const out: Record<string, [number, number]> = {};
    for (const [joint, [x, y]] of Object.entries(data.latest.joints)) {
      out[joint] = [
        pad + ((x - minX) / spanX) * (w - 2 * pad),
        pad + ((y - minY) / spanY) * (h - 2 * pad),
      ];
    }
    return { positions: out, width: w, height: h };
  }, [data]);

  if (loading && !data)
    return (
      <div style={{ padding: 16, color: "var(--text-2)" }}>
        loading skeletal graph…
      </div>
    );
  if (error)
    return (
      <div style={{ padding: 16, color: "var(--err)" }}>{error.message}</div>
    );
  if (!data) return null;

  return (
    <section style={{ padding: 16 }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "240px 1fr",
          gap: 16,
          marginBottom: 18,
        }}
      >
        <div>
          <h3
            style={{
              margin: "0 0 10px",
              fontSize: 13,
              textTransform: "uppercase",
              letterSpacing: 1,
              color: "var(--text-2)",
            }}
          >
            stick figure
          </h3>
          {scaled && data.latest ? (
            <svg
              viewBox={`0 0 ${scaled.width} ${scaled.height}`}
              width={220}
              height={300}
              style={{
                background: "var(--bg-1)",
                border: "1px solid var(--border-1)",
                borderRadius: "var(--r2)",
                display: "block",
              }}
            >
              {/* bones */}
              {data.bones.map(([a, b], idx) => {
                const pa = scaled.positions[a];
                const pb = scaled.positions[b];
                if (!pa || !pb) return null;
                return (
                  <line
                    key={idx}
                    x1={pa[0]}
                    y1={pa[1]}
                    x2={pb[0]}
                    y2={pb[1]}
                    stroke="var(--border-2)"
                    strokeWidth={0.6}
                  />
                );
              })}
              {/* joints */}
              {Object.entries(scaled.positions).map(([joint, [x, y]]) => {
                const wound = data.latest!.wounds[joint] ?? 0;
                const r = 2.2 + wound * 2.5;
                return (
                  <g key={joint}>
                    <circle
                      cx={x}
                      cy={y}
                      r={r}
                      fill={woundColor(wound)}
                      stroke="var(--bg-0)"
                      strokeWidth={0.3}
                    >
                      <title>
                        {joint} — wound {formatScore(wound)}
                      </title>
                    </circle>
                  </g>
                );
              })}
            </svg>
          ) : (
            <div style={{ color: "var(--text-2)", fontSize: 12 }}>
              no joint observations yet
            </div>
          )}
        </div>

        <div>
          <h3
            style={{
              margin: "0 0 10px",
              fontSize: 13,
              textTransform: "uppercase",
              letterSpacing: 1,
              color: "var(--text-2)",
            }}
          >
            left / right asymmetry
          </h3>
          {data.asymmetries.length === 0 ? (
            <div
              style={{
                fontStyle: "italic",
                color: "var(--text-2)",
                fontSize: 12,
              }}
            >
              no paired joints observed yet
            </div>
          ) : (
            data.asymmetries.map((a, idx) => {
              const label = `${a.pair[0]
                .replace("_l", "")
                .replace("_r", "")}`;
              return (
                <div
                  key={idx}
                  style={{
                    marginBottom: 10,
                    padding: 8,
                    background: "var(--bg-1)",
                    border: "1px solid var(--border-1)",
                    borderRadius: "var(--r1)",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 600,
                      marginBottom: 4,
                      textTransform: "capitalize",
                    }}
                  >
                    {label}
                  </div>
                  <ConfidenceBar
                    label="motion asymmetry"
                    value={a.motion_asymmetry}
                    color={
                      a.motion_asymmetry > 0.5
                        ? "var(--prio-immediate)"
                        : "var(--prio-delayed)"
                    }
                  />
                  <ConfidenceBar
                    label="wound asymmetry"
                    value={a.wound_asymmetry}
                    color={
                      a.wound_asymmetry > 0.5
                        ? "var(--prio-immediate)"
                        : "var(--accent)"
                    }
                  />
                </div>
              );
            })
          )}
        </div>
      </div>

      <h3
        style={{
          margin: "0 0 10px",
          fontSize: 13,
          textTransform: "uppercase",
          letterSpacing: 1,
          color: "var(--text-2)",
        }}
      >
        per-joint trends
      </h3>
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
            <th style={{ padding: 4 }}>joint</th>
            <th style={{ padding: 4 }}>n obs</th>
            <th style={{ padding: 4 }}>motion</th>
            <th style={{ padding: 4 }}>wound mean</th>
            <th style={{ padding: 4 }}>wound slope</th>
          </tr>
        </thead>
        <tbody>
          {Object.values(data.trends)
            .filter((t: JointTrend) => t.n_observations > 0)
            .map((t: JointTrend) => (
              <tr key={t.joint}>
                <td style={{ padding: 4 }}>{t.joint}</td>
                <td style={{ padding: 4, color: "var(--text-1)" }}>
                  {t.n_observations}
                </td>
                <td
                  style={{
                    padding: 4,
                    color:
                      t.motion_score > 0.3 ? "var(--ok)" : "var(--text-1)",
                  }}
                >
                  {t.motion_score.toFixed(3)}
                </td>
                <td
                  style={{
                    padding: 4,
                    color: woundColor(t.wound_mean),
                  }}
                >
                  {t.wound_mean.toFixed(3)}
                </td>
                <td
                  style={{
                    padding: 4,
                    color:
                      t.wound_slope > 0.01
                        ? "var(--prio-immediate)"
                        : t.wound_slope < -0.01
                          ? "var(--ok)"
                          : "var(--text-2)",
                  }}
                >
                  {t.wound_slope >= 0 ? "+" : ""}
                  {t.wound_slope.toFixed(4)}
                </td>
              </tr>
            ))}
        </tbody>
      </table>
    </section>
  );
}
