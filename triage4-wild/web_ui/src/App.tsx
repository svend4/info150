import { useEffect, useState } from "react";
import { api } from "./api";
import CameraPanel from "./CameraPanel";
import type { Alert, AlertLevel, Report, Score } from "./types";

const LEVEL_COLOR: Record<AlertLevel, string> = {
  ok: "#27ae60", watch: "#e6a23c", urgent: "#e74c3c",
};

function Bar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = pct < 45 ? "#e74c3c" : pct < 65 ? "#e6a23c" : "#27ae60";
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span style={{ opacity: 0.85 }}>{label}</span><span>{value.toFixed(2)}</span>
      </div>
      <div style={{ height: 6, background: "#3a3326", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, background: color, height: "100%" }} />
      </div>
    </div>
  );
}

export default function App() {
  const [report, setReport] = useState<Report | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<(Score & { alerts: Alert[] }) | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try { setError(null); const d = await api.report(); setReport(d);
      if (!selected && d.scores.length) setSelected(d.scores[0].obs_token); }
    catch (e) { setError((e as Error).message); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!selected) return;
    api.observation(selected).then(setDetail).catch((e) => setError((e as Error).message));
  }, [selected]);

  const reload = async () => { await api.reload(); setSelected(null); setDetail(null); await load(); };

  if (error) return (
    <div style={{ padding: 24, color: "#ff8c8c" }}>
      Error: <code>{error}</code>
      <p>Backend running? <code>uvicorn triage4_wild.ui.dashboard_api:app</code></p>
    </div>
  );
  if (!report) return <div style={{ padding: 24 }}>Loading…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>triage4-wild</h1>
        <span style={{ opacity: 0.7 }}>
          reserve <code>{report.reserve_id}</code> · {report.observation_count} obs · {report.alerts.length} alerts
        </span>
        <button onClick={reload} style={{ marginLeft: "auto", padding: "6px 14px",
          background: "#8b6f1d", color: "white", border: 0, borderRadius: 4, cursor: "pointer" }}>
          Re-seed demo
        </button>
      </header>
      <CameraPanel onAnalyzed={load} />
      <section style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        {(["ok", "watch", "urgent"] as const).map((lvl) => (
          <div key={lvl} style={{ flex: 1, minWidth: 160, background: "#2a2418",
            padding: 12, borderRadius: 6, borderLeft: `4px solid ${LEVEL_COLOR[lvl]}` }}>
            <div style={{ fontSize: 12, opacity: 0.7, textTransform: "uppercase" }}>{lvl}</div>
            <div style={{ fontSize: 28, fontWeight: 600 }}>{report.level_counts[lvl]}</div>
          </div>
        ))}
      </section>
      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <div style={{ background: "#2a2418", borderRadius: 6, padding: 8, maxHeight: 600, overflowY: "auto" }}>
          {report.scores.map((s) => (
            <button key={s.obs_token} onClick={() => setSelected(s.obs_token)}
              style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px",
                margin: "2px 0", background: selected === s.obs_token ? "#3a3326" : "transparent",
                color: "#ede4d4", border: 0, borderLeft: `4px solid ${LEVEL_COLOR[s.alert_level]}`,
                borderRadius: 4, cursor: "pointer", fontSize: 13 }}>
              <div style={{ fontWeight: 600 }}>{s.obs_token}</div>
              <div style={{ fontSize: 11, opacity: 0.75 }}>
                {s.alert_level} · overall {s.overall.toFixed(2)}
              </div>
            </button>
          ))}
        </div>
        <div style={{ background: "#2a2418", borderRadius: 6, padding: 16, minHeight: 300 }}>
          {detail ? (<>
            <h2 style={{ marginTop: 0, fontSize: 18 }}>
              {detail.obs_token}{" "}
              <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 3,
                background: LEVEL_COLOR[detail.alert_level], marginLeft: 8 }}>
                {detail.alert_level}
              </span>
            </h2>
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Channels</h3>
            <Bar value={detail.gait_safety} label="Gait" />
            <Bar value={detail.thermal_safety} label="Thermal" />
            <Bar value={detail.postural_safety} label="Posture" />
            <Bar value={detail.body_condition_safety} label="Body condition" />
            <Bar value={detail.threat_signal} label="Threat (1.0 = no flags)" />
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Alerts ({detail.alerts.length})</h3>
            {detail.alerts.length === 0 ? <p style={{ opacity: 0.6 }}><i>none</i></p> : (
              <ul style={{ paddingLeft: 18 }}>
                {detail.alerts.map((a, i) => (
                  <li key={i}>
                    <span style={{ color: LEVEL_COLOR[a.level], fontWeight: 600,
                      textTransform: "uppercase", marginRight: 6 }}>{a.level}</span>
                    <code>{a.kind}</code> {a.text}
                  </li>
                ))}
              </ul>
            )}
          </>) : <p style={{ opacity: 0.6 }}>Select an observation.</p>}
        </div>
      </div>
      <footer style={{ marginTop: 32, fontSize: 12, opacity: 0.5 }}>
        triage4-wild · sibling-level dashboard · MIT license
      </footer>
    </div>
  );
}
