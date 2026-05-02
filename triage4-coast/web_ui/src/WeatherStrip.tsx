// Top-of-dashboard weather strip — small icons + numbers per channel.
// Pulls a cached snapshot from /coast/weather every 60 s and offers a
// manual "refresh" that hits /coast/weather/refresh against the
// configured provider (mock by default, OpenWeather if API key set).

import { useEffect, useState } from "react";
import { api, type WeatherSnapshot } from "./api";

function fmt(v: number | null | undefined, digits = 1, suffix = ""): string {
  if (v === null || v === undefined) return "—";
  return v.toFixed(digits) + suffix;
}

function uvColor(uv: number | null | undefined): string {
  if (uv === null || uv === undefined) return "var(--text-disabled)";
  if (uv >= 8) return "#e74c3c";
  if (uv >= 6) return "#e6a23c";
  if (uv >= 3) return "#f4d03f";
  return "#27ae60";
}

export default function WeatherStrip({ refreshMs = 60_000 }: { refreshMs?: number }) {
  const [snap, setSnap] = useState<WeatherSnapshot | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lat, setLat] = useState(43.7);
  const [lon, setLon] = useState(7.3);
  const [actuated, setActuated] = useState<number | null>(null);

  const load = async () => {
    try {
      const r = await api.weatherLatest();
      setSnap(r.snapshot);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, refreshMs);
    return () => clearInterval(t);
  }, [refreshMs]);

  const refresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      const r = await api.weatherRefresh(lat, lon, true);
      setSnap(r.snapshot);
      setActuated(r.actuated_count);
      setTimeout(() => setActuated(null), 4000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRefreshing(false);
    }
  };

  if (!snap) {
    return (
      <div style={{
        background: "var(--bg)", borderRadius: 6, padding: 10, marginBottom: 12,
        display: "flex", justifyContent: "space-between", alignItems: "center",
        fontSize: 12, color: "var(--text-muted)",
      }}>
        <span>weather: no snapshot yet — click refresh</span>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <input type="number" step="0.01" value={lat}
            onChange={(e) => setLat(parseFloat(e.target.value) || 0)}
            style={{ width: 70, ...inputStyle }} />
          <input type="number" step="0.01" value={lon}
            onChange={(e) => setLon(parseFloat(e.target.value) || 0)}
            style={{ width: 70, ...inputStyle }} />
          <button onClick={refresh} disabled={refreshing} style={btnStyle}>
            {refreshing ? "…" : "↻"}
          </button>
        </div>
        {error && <span style={{ color: "var(--danger-text)" }}>{error}</span>}
      </div>
    );
  }

  const ageSec = Math.round(Date.now() / 1000 - snap.ts_unix);

  return (
    <div style={{
      background: "var(--bg)", borderRadius: 6, padding: 10, marginBottom: 12,
      display: "flex", flexWrap: "wrap", gap: 14, alignItems: "center",
      fontSize: 12, color: "var(--text)",
    }}>
      <Stat icon="🌡️" label="temp" value={fmt(snap.air_temp_c, 1, "°C")} />
      <Stat icon="💨" label="wind" value={fmt(snap.wind_speed_mps, 1, " m/s")} />
      <Stat icon="☀️" label="UV" value={fmt(snap.uv_index, 1)}
        valueColor={uvColor(snap.uv_index)} />
      <Stat icon="☁️"
        label="cloud"
        value={snap.cloud_cover === null
          ? "—" : `${Math.round((snap.cloud_cover ?? 0) * 100)}%`} />
      <Stat icon="⚡" label="lightning"
        value={String(snap.lightning_strikes_5min)}
        valueColor={snap.lightning_strikes_5min > 0 ? "#e74c3c" : "var(--text)"} />
      <span style={{ opacity: 0.7, fontStyle: "italic" }}>
        {snap.forecast_summary}
      </span>
      <span style={{ marginLeft: "auto", display: "flex", gap: 6,
        alignItems: "center" }}>
        <span style={{ opacity: 0.6 }}>
          {snap.provider} · {ageSec}s ago
        </span>
        <input type="number" step="0.01" value={lat}
          onChange={(e) => setLat(parseFloat(e.target.value) || 0)}
          style={{ width: 70, ...inputStyle }} title="latitude" />
        <input type="number" step="0.01" value={lon}
          onChange={(e) => setLon(parseFloat(e.target.value) || 0)}
          style={{ width: 70, ...inputStyle }} title="longitude" />
        <button onClick={refresh} disabled={refreshing} style={btnStyle}>
          {refreshing ? "…" : "↻"}
        </button>
      </span>
      {actuated !== null && (
        <span style={{ color: "#e6a23c" }}>
          ✓ {actuated} auto-broadcast{actuated === 1 ? "" : "s"} fired
        </span>
      )}
      {error && (
        <span style={{ color: "var(--danger-text)" }}>{error}</span>
      )}
    </div>
  );
}

function Stat({ icon, label, value, valueColor = "var(--text)" }: {
  icon: string; label: string; value: string; valueColor?: string;
}) {
  return (
    <span style={{ display: "flex", gap: 4, alignItems: "baseline" }}>
      <span style={{ fontSize: 14 }}>{icon}</span>
      <span style={{ opacity: 0.6 }}>{label}</span>
      <span style={{ fontWeight: 600, color: valueColor }}>{value}</span>
    </span>
  );
}

const inputStyle: React.CSSProperties = {
  padding: 4, background: "var(--surface-2)", color: "var(--text)",
  border: "1px solid var(--primary)", borderRadius: 4, fontSize: 11,
};
const btnStyle: React.CSSProperties = {
  padding: "4px 10px", background: "var(--primary)", color: "#fff",
  border: 0, borderRadius: 4, cursor: "pointer", fontSize: 12,
};
