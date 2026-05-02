import { useEffect, useState } from "react";
import { api } from "./api";
import CameraPanel from "./CameraPanel";
import type { Alert, AlertLevel, Report, Score } from "./types";

const LEVEL_COLOR: Record<AlertLevel, string> = {
  ok: "#27ae60", caution: "#e6a23c", critical: "#e74c3c",
};

function RiskBar({ value, label }: { value: number; label: string }) {
  // Drive scores are RISK scores — 0 = good, 1 = bad. Invert color logic.
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = pct > 65 ? "#e74c3c" : pct > 35 ? "#e6a23c" : "#27ae60";
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span style={{ opacity: 0.85 }}>{label}</span><span>{value.toFixed(2)}</span>
      </div>
      <div style={{ height: 6, background: "#1f2929", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, background: color, height: "100%" }} />
      </div>
    </div>
  );
}

export default function App() {
  const [report, setReport] = useState<Report | null>(null);
  const [selected, setSelected] = useState<number>(0);
  const [detail, setDetail] = useState<(Score & { alerts: Alert[] }) | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try { setError(null); const d = await api.report(); setReport(d); }
    catch (e) { setError((e as Error).message); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!report) return;
    api.window(selected).then(setDetail).catch((e) => setError((e as Error).message));
  }, [selected, report]);

  const reload = async () => { setSelected(0); setDetail(null); await api.reload(); await load(); };

  if (error) return (
    <div style={{ padding: 24, color: "#ff8c8c" }}>
      Error: <code>{error}</code>
      <p>Backend running? <code>uvicorn triage4_drive.ui.dashboard_api:app</code></p>
    </div>
  );
  if (!report) return <div style={{ padding: 24 }}>Loading…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>triage4-drive</h1>
        <span style={{ opacity: 0.7 }}>
          session <code>{report.session_id}</code> · {report.window_count} windows · {report.alerts.length} alerts
        </span>
        <button onClick={reload} style={{ marginLeft: "auto", padding: "6px 14px",
          background: "#1f5fbf", color: "white", border: 0, borderRadius: 4, cursor: "pointer" }}>
          Re-seed demo
        </button>
      </header>
      <CameraPanel onAnalyzed={load} />
      <section style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        {(["ok", "caution", "critical"] as const).map((lvl) => (
          <div key={lvl} style={{ flex: 1, minWidth: 160, background: "#161e1e",
            padding: 12, borderRadius: 6, borderLeft: `4px solid ${LEVEL_COLOR[lvl]}` }}>
            <div style={{ fontSize: 12, opacity: 0.7, textTransform: "uppercase" }}>{lvl}</div>
            <div style={{ fontSize: 28, fontWeight: 600 }}>{report.level_counts[lvl]}</div>
          </div>
        ))}
      </section>
      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <div style={{ background: "#161e1e", borderRadius: 6, padding: 8, maxHeight: 600, overflowY: "auto" }}>
          {report.scores.map((s, i) => (
            <button key={i} onClick={() => setSelected(i)}
              style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px",
                margin: "2px 0", background: selected === i ? "#1f2929" : "transparent",
                color: "#e2eae2", border: 0, borderLeft: `4px solid ${LEVEL_COLOR[s.alert_level]}`,
                borderRadius: 4, cursor: "pointer", fontSize: 13 }}>
              <div style={{ fontWeight: 600 }}>w{i.toString().padStart(2, "0")}</div>
              <div style={{ fontSize: 11, opacity: 0.75 }}>
                {s.alert_level} · risk {s.overall.toFixed(2)}
              </div>
            </button>
          ))}
        </div>
        <div style={{ background: "#161e1e", borderRadius: 6, padding: 16, minHeight: 300 }}>
          {detail ? (<>
            <h2 style={{ marginTop: 0, fontSize: 18 }}>
              w{selected.toString().padStart(2, "0")}{" "}
              <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 3,
                background: LEVEL_COLOR[detail.alert_level], marginLeft: 8 }}>
                {detail.alert_level}
              </span>
            </h2>
            <p style={{ opacity: 0.7, fontSize: 12 }}>
              <i>Note: drive channels are RISK scores — higher = worse (drowsiness, distraction, incapacitation).</i>
            </p>
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Channels</h3>
            <RiskBar value={detail.perclos} label="PERCLOS (eye closure)" />
            <RiskBar value={detail.distraction} label="Distraction" />
            <RiskBar value={detail.incapacitation} label="Incapacitation" />
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Session-level alerts ({detail.alerts.length})</h3>
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
          </>) : <p style={{ opacity: 0.6 }}>Select a window.</p>}
        </div>
      </div>
      <footer style={{ marginTop: 32, fontSize: 12, opacity: 0.5 }}>
        triage4-drive · sibling-level dashboard · MIT license
      </footer>
    </div>
  );
}
