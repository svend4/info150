// Forecast tab: casualty-level + mission-level projection. User
// picks a casualty and an N-minute horizon; the backend runs both
// ForecastLayer.project_casualty and project_mission.

import { useEffect, useState } from "react";

import {
  fetchCasualties,
  fetchCasualtyForecast,
  fetchMissionForecast,
} from "../api/endpoints";
import ConfidenceBar from "../components/casualties/ConfidenceBar";
import { useResource } from "../hooks/useResource";
import { priorityColor } from "../util/priority";
import { formatConfidence } from "../util/format";

const HORIZONS = [1, 3, 5, 10, 15];

const MISSION_CHANNELS: { key: string; label: string }[] = [
  { key: "casualty_density", label: "casualty density" },
  { key: "immediate_fraction", label: "immediate fraction" },
  { key: "unresolved_sector_fraction", label: "unresolved sectors" },
  { key: "medic_utilisation", label: "medic utilisation" },
  { key: "time_budget_burn", label: "time burn" },
];

export default function ForecastPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [horizon, setHorizon] = useState<number>(5);

  const casualtiesList = useResource(fetchCasualties);
  const casualtyIds = (casualtiesList.data ?? []).map((c) => c.id);

  useEffect(() => {
    if (selectedId === null && casualtyIds.length > 0) {
      setSelectedId(casualtyIds[0]);
    }
  }, [casualtyIds, selectedId]);

  const casualtyForecast = useResource(
    (signal) =>
      selectedId
        ? fetchCasualtyForecast(selectedId, horizon, signal)
        : Promise.reject(new Error("no casualty selected")),
    [selectedId, horizon],
  );

  const missionForecast = useResource(
    (signal) => fetchMissionForecast(horizon, signal),
    [horizon],
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
          <h1 style={{ margin: 0, fontSize: 22 }}>Forecast</h1>
          <div
            style={{ color: "var(--text-2)", fontSize: 12, marginTop: 4 }}
          >
            Forward projection for a single casualty and for the mission
            as a whole. K3-3.3.
          </div>
        </div>
      </header>

      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "center",
          marginBottom: 16,
          padding: 12,
          background: "var(--bg-1)",
          border: "1px solid var(--border-1)",
          borderRadius: "var(--r2)",
          fontSize: 12,
        }}
      >
        <span style={{ color: "var(--text-2)" }}>casualty</span>
        <select
          value={selectedId ?? ""}
          onChange={(e) => setSelectedId(e.target.value || null)}
        >
          {casualtyIds.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
        <span style={{ color: "var(--text-2)", marginLeft: 16 }}>
          horizon
        </span>
        {HORIZONS.map((h) => (
          <button
            key={h}
            aria-pressed={horizon === h}
            onClick={() => setHorizon(h)}
            style={{ fontSize: 11, padding: "4px 10px" }}
          >
            {h} min
          </button>
        ))}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
        }}
      >
        <Panel title={`Casualty ${selectedId ?? "—"}`}>
          {casualtyForecast.loading && !casualtyForecast.data && (
            <div style={{ color: "var(--text-2)", fontStyle: "italic" }}>
              projecting…
            </div>
          )}
          {casualtyForecast.error && (
            <div style={{ color: "var(--err)", fontSize: 12 }}>
              {casualtyForecast.error.message}
            </div>
          )}
          {casualtyForecast.data && (
            <CasualtyProjection forecast={casualtyForecast.data} />
          )}
        </Panel>

        <Panel title="Mission">
          {missionForecast.loading && !missionForecast.data && (
            <div style={{ color: "var(--text-2)", fontStyle: "italic" }}>
              projecting…
            </div>
          )}
          {missionForecast.error && (
            <div style={{ color: "var(--err)", fontSize: 12 }}>
              {missionForecast.error.message}
            </div>
          )}
          {missionForecast.data && (
            <MissionProjection forecast={missionForecast.data} />
          )}
        </Panel>
      </div>
    </section>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      style={{
        padding: 16,
        background: "var(--bg-1)",
        border: "1px solid var(--border-1)",
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

function CasualtyProjection({
  forecast,
}: {
  forecast: {
    projected_priority: string;
    projected_score: number;
    slope_per_minute: number;
    confidence: number;
    score_history: number[];
    reasons: string[];
  };
}) {
  const points = [...forecast.score_history, forecast.projected_score];
  return (
    <>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 12,
        }}
      >
        <div>
          <div
            style={{
              color: priorityColor(forecast.projected_priority),
              fontSize: 22,
              fontWeight: 700,
              textTransform: "uppercase",
            }}
          >
            {forecast.projected_priority}
          </div>
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              color: "var(--text-1)",
              marginTop: 2,
            }}
          >
            projected score {forecast.projected_score.toFixed(3)}
          </div>
        </div>
        <div style={{ textAlign: "right", fontSize: 11 }}>
          <div style={{ color: "var(--text-2)" }}>slope / min</div>
          <div style={{ fontFamily: "var(--font-mono)" }}>
            {forecast.slope_per_minute >= 0 ? "+" : ""}
            {forecast.slope_per_minute.toFixed(4)}
          </div>
        </div>
      </div>

      <ConfidenceBar
        label="trend stability (R²)"
        value={forecast.confidence}
      />

      <Sparkline values={points} highlight={points.length - 1} />

      {forecast.reasons.length > 0 && (
        <ul
          style={{
            marginTop: 12,
            paddingLeft: 18,
            color: "var(--text-1)",
            fontSize: 12,
          }}
        >
          {forecast.reasons.map((r, idx) => (
            <li key={idx}>{r}</li>
          ))}
        </ul>
      )}
    </>
  );
}

function MissionProjection({
  forecast,
}: {
  forecast: {
    projected_signature: Record<string, number>;
    projected_priority: string;
    projected_score: number;
    per_channel_slope: Record<string, number>;
    reasons: string[];
  };
}) {
  return (
    <>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 12,
        }}
      >
        <div
          style={{
            color:
              forecast.projected_priority === "escalate"
                ? "var(--prio-immediate)"
                : forecast.projected_priority === "sustain"
                  ? "var(--prio-delayed)"
                  : "var(--prio-minimal)",
            fontSize: 22,
            fontWeight: 700,
            textTransform: "uppercase",
          }}
        >
          {forecast.projected_priority.replace(/_/g, " ")}
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ color: "var(--text-2)", fontSize: 11 }}>
            projected score
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}>
            {forecast.projected_score.toFixed(3)}
          </div>
        </div>
      </div>

      {MISSION_CHANNELS.map(({ key, label }) => {
        const value = forecast.projected_signature[key] ?? 0;
        const slope = forecast.per_channel_slope[key] ?? 0;
        return (
          <div key={key} style={{ marginBottom: 8 }}>
            <ConfidenceBar label={label} value={value} />
            <div
              style={{
                fontSize: 10,
                fontFamily: "var(--font-mono)",
                color: slope > 0 ? "var(--prio-immediate)" : "var(--text-2)",
                textAlign: "right",
                marginTop: 1,
              }}
            >
              slope: {slope >= 0 ? "+" : ""}
              {slope.toFixed(4)}/min
            </div>
          </div>
        );
      })}

      {forecast.reasons.length > 0 && (
        <ul
          style={{
            marginTop: 12,
            paddingLeft: 18,
            color: "var(--text-1)",
            fontSize: 12,
          }}
        >
          {forecast.reasons.map((r, idx) => (
            <li key={idx}>{r}</li>
          ))}
        </ul>
      )}
    </>
  );
}

function Sparkline({
  values,
  highlight,
  width = 320,
  height = 80,
}: {
  values: number[];
  highlight: number;
  width?: number;
  height?: number;
}) {
  if (values.length === 0) return null;
  const pad = 6;
  const w = width - pad * 2;
  const h = height - pad * 2;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(0.01, max - min);
  const pts = values.map((v, i) => {
    const x = pad + (i / Math.max(1, values.length - 1)) * w;
    const y = pad + h - ((v - min) / range) * h;
    return { x, y, v };
  });
  const d = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  return (
    <svg
      width={width}
      height={height}
      style={{
        background: "var(--bg-0)",
        borderRadius: "var(--r1)",
        marginTop: 8,
      }}
    >
      <rect
        x={pad + (w * highlight) / Math.max(1, pts.length - 1) - 1}
        y={pad}
        width={2}
        height={h}
        fill="var(--accent-dim)"
      />
      <path d={d} stroke="var(--accent)" strokeWidth={1.5} fill="none" />
      {pts.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={i === highlight ? 3.5 : 2}
          fill={i === highlight ? "var(--prio-immediate)" : "var(--accent)"}
        />
      ))}
    </svg>
  );
}
