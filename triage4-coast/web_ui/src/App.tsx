import { useEffect, useState } from "react";
import { api } from "./api";
import CameraHealthBar from "./CameraHealthBar";
import CameraPanel from "./CameraPanel";
import HistoryChart from "./HistoryChart";
import OpsConsole from "./OpsConsole";
import ZoneGrid from "./ZoneGrid";
import type { Alert, AlertLevel, Report, Score } from "./types";

type ViewMode = "list" | "grid" | "ops";

const VIEW_LABELS: Record<ViewMode, string> = {
  list: "list/detail",
  grid: "grid",
  ops: "ops console",
};
const NEXT_VIEW: Record<ViewMode, ViewMode> = {
  list: "grid", grid: "ops", ops: "list",
};

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
      <div style={{ height: 6, background: "#2a3346", borderRadius: 3, overflow: "hidden" }}>
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
  const [view, setView] = useState<ViewMode>("list");

  const load = async () => {
    try { setError(null); const d = await api.report(); setReport(d);
      if (!selected && d.scores.length) setSelected(d.scores[0].zone_id); }
    catch (e) { setError((e as Error).message); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!selected) return;
    api.zone(selected).then(setDetail).catch((e) => setError((e as Error).message));
  }, [selected]);

  const reload = async () => { await api.reload(); setSelected(null); setDetail(null); await load(); };

  if (error) return (
    <div style={{ padding: 24, color: "#ff8c8c" }}>
      Error: <code>{error}</code>
      <p>Backend running? <code>uvicorn triage4_coast.ui.dashboard_api:app</code></p>
    </div>
  );
  if (!report) return <div style={{ padding: 24 }}>Loading…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>triage4-coast</h1>
        <span style={{ opacity: 0.7 }}>
          coast <code>{report.coast_id}</code> · {report.zone_count} zones · {report.alerts.length} alerts
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <button onClick={() => setView(NEXT_VIEW[view])}
            style={{ padding: "6px 14px",
              background: "#22293f", color: "#dde7df", border: "1px solid #5c7cfa",
              borderRadius: 4, cursor: "pointer", fontSize: 13 }}>
            view: {VIEW_LABELS[view]} ↔
          </button>
          <button onClick={reload} style={{ padding: "6px 14px",
            background: "#1f5fbf", color: "white", border: 0, borderRadius: 4,
            cursor: "pointer" }}>
            Re-seed demo
          </button>
        </div>
      </header>
      <CameraHealthBar />
      <CameraPanel onAnalyzed={load} />
      <section style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        {(["ok", "watch", "urgent"] as const).map((lvl) => (
          <div key={lvl} style={{ flex: 1, minWidth: 160, background: "#181f33",
            padding: 12, borderRadius: 6, borderLeft: `4px solid ${LEVEL_COLOR[lvl]}` }}>
            <div style={{ fontSize: 12, opacity: 0.7, textTransform: "uppercase" }}>{lvl}</div>
            <div style={{ fontSize: 28, fontWeight: 600 }}>{report.level_counts[lvl]}</div>
          </div>
        ))}
      </section>
      {view === "ops" ? (
        <OpsConsole scores={report.scores} />
      ) : view === "grid" ? (
        <ZoneGrid scores={report.scores} />
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
          <div style={{ background: "#181f33", borderRadius: 6, padding: 8, maxHeight: 600, overflowY: "auto" }}>
            {report.scores.map((s) => (
              <button key={s.zone_id} onClick={() => setSelected(s.zone_id)}
                style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px",
                  margin: "2px 0", background: selected === s.zone_id ? "#26304a" : "transparent",
                  color: "#e4e8f0", border: 0, borderLeft: `4px solid ${LEVEL_COLOR[s.alert_level]}`,
                  borderRadius: 4, cursor: "pointer", fontSize: 13 }}>
                <div style={{ fontWeight: 600 }}>{s.zone_id}</div>
                <div style={{ fontSize: 11, opacity: 0.75 }}>
                  {s.alert_level} · overall {s.overall.toFixed(2)}
                </div>
              </button>
            ))}
          </div>
          <div style={{ background: "#181f33", borderRadius: 6, padding: 16, minHeight: 300 }}>
            {detail ? (<>
              <h2 style={{ marginTop: 0, fontSize: 18 }}>
                {detail.zone_id}{" "}
                <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 3,
                  background: LEVEL_COLOR[detail.alert_level], marginLeft: 8 }}>
                  {detail.alert_level}
                </span>
              </h2>
              <h3 style={{ fontSize: 14, marginTop: 16 }}>Channels</h3>
              <Bar value={detail.density_safety} label="Density" />
              <Bar value={detail.drowning_safety} label="Drowning-risk safety" />
              <Bar value={detail.sun_safety} label="Sun" />
              <Bar value={detail.lost_child_safety} label="Lost-child" />
              <Bar value={detail.fall_event_safety} label="Fall-event" />
              <Bar value={detail.stationary_person_safety} label="Stationary-person" />
              <Bar value={detail.flow_anomaly_safety} label="Flow-anomaly" />
              <Bar value={detail.slip_risk_safety} label="Slip-risk" />
              <h3 style={{ fontSize: 14, marginTop: 16 }}>History (overall, last 1 h)</h3>
              <HistoryChart zoneId={detail.zone_id} channel="overall" hours={1} />
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
            </>) : <p style={{ opacity: 0.6 }}>Select a zone to see channels + alerts.</p>}
          </div>
        </div>
      )}
      <footer style={{ marginTop: 32, fontSize: 12, opacity: 0.5 }}>
        triage4-coast · sibling-level dashboard · MIT license
      </footer>
    </div>
  );
}
