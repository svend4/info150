import { useEffect, useState } from "react";
import { api } from "./api";
import CameraPanel from "./CameraPanel";
import type { Report, RiskBand, SessionDetail } from "./types";

const BAND_COLOR: Record<RiskBand, string> = {
  steady: "#27ae60", monitor: "#e6a23c", hold: "#e74c3c",
};

function Bar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = pct < 45 ? "#e74c3c" : pct < 65 ? "#e6a23c" : "#27ae60";
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span style={{ opacity: 0.85 }}>{label}</span><span>{value.toFixed(2)}</span>
      </div>
      <div style={{ height: 6, background: "#22273a", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, background: color, height: "100%" }} />
      </div>
    </div>
  );
}

export default function App() {
  const [report, setReport] = useState<Report | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try { setError(null); const d = await api.report(); setReport(d);
      if (!selected && d.sessions.length) setSelected(d.sessions[0].athlete_token); }
    catch (e) { setError((e as Error).message); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!selected) return;
    api.session(selected).then(setDetail).catch((e) => setError((e as Error).message));
  }, [selected]);

  const reload = async () => { await api.reload(); setSelected(null); setDetail(null); await load(); };

  if (error) return (
    <div style={{ padding: 24, color: "#ff8c8c" }}>
      Error: <code>{error}</code>
      <p>Backend running? <code>uvicorn triage4_sport.ui.dashboard_api:app</code></p>
    </div>
  );
  if (!report) return <div style={{ padding: 24 }}>Loading…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>triage4-sport</h1>
        <span style={{ opacity: 0.7 }}>{report.session_count} athlete sessions</span>
        <button onClick={reload} style={{ marginLeft: "auto", padding: "6px 14px",
          background: "#3a4a8b", color: "white", border: 0, borderRadius: 4, cursor: "pointer" }}>
          Re-seed demo
        </button>
      </header>
      <CameraPanel onAnalyzed={load} />
      <section style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        {(["steady", "monitor", "hold"] as const).map((b) => (
          <div key={b} style={{ flex: 1, minWidth: 160, background: "#181d33",
            padding: 12, borderRadius: 6, borderLeft: `4px solid ${BAND_COLOR[b]}` }}>
            <div style={{ fontSize: 12, opacity: 0.7, textTransform: "uppercase" }}>{b}</div>
            <div style={{ fontSize: 28, fontWeight: 600 }}>{report.band_counts[b]}</div>
          </div>
        ))}
      </section>
      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <div style={{ background: "#181d33", borderRadius: 6, padding: 8, maxHeight: 600, overflowY: "auto" }}>
          {report.sessions.map((s) => (
            <button key={s.athlete_token} onClick={() => setSelected(s.athlete_token)}
              style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px",
                margin: "2px 0", background: selected === s.athlete_token ? "#22273a" : "transparent",
                color: "#dee3f0", border: 0, borderLeft: `4px solid ${BAND_COLOR[s.assessment.risk_band]}`,
                borderRadius: 4, cursor: "pointer", fontSize: 13 }}>
              <div style={{ fontWeight: 600 }}>{s.athlete_token}</div>
              <div style={{ fontSize: 11, opacity: 0.75 }}>
                {s.assessment.risk_band} · overall {s.assessment.overall.toFixed(2)}
                {s.has_physician_alert && " · physician"}
              </div>
            </button>
          ))}
        </div>
        <div style={{ background: "#181d33", borderRadius: 6, padding: 16, minHeight: 300 }}>
          {detail ? (<>
            <h2 style={{ marginTop: 0, fontSize: 18 }}>
              {detail.athlete_token}{" "}
              <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 3,
                background: BAND_COLOR[detail.assessment.risk_band], marginLeft: 8 }}>
                {detail.assessment.risk_band}
              </span>
            </h2>
            {detail.sport && (
              <p style={{ opacity: 0.85 }}>
                <b>{detail.sport}</b>
                {detail.session_duration_s !== null &&
                  ` · ${Math.round(detail.session_duration_s)}s session`}
              </p>
            )}
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Channels</h3>
            <Bar value={detail.assessment.form_asymmetry_safety} label="Form asymmetry" />
            <Bar value={detail.assessment.workload_load_safety} label="Workload" />
            <Bar value={detail.assessment.recovery_hr_safety} label="Recovery HR" />
            <Bar value={detail.assessment.baseline_deviation_safety} label="Baseline deviation" />
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Coach messages ({detail.coach_messages.length})</h3>
            <ul style={{ paddingLeft: 18 }}>
              {detail.coach_messages.map((m, i) => <li key={i}>{m.text}</li>)}
            </ul>
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Trainer notes ({detail.trainer_notes.length})</h3>
            <ul style={{ paddingLeft: 18 }}>
              {detail.trainer_notes.map((n, i) => <li key={i}>{n.text}</li>)}
            </ul>
            {detail.physician_alert && (<>
              <h3 style={{ fontSize: 14, marginTop: 16, color: "#e6a23c" }}>Physician alert</h3>
              <p>{detail.physician_alert.text}</p>
              {detail.physician_alert.reasoning_trace && (
                <pre style={{ whiteSpace: "pre-wrap", background: "#0e1124",
                  padding: 12, borderRadius: 4, fontSize: 12 }}>
                  {detail.physician_alert.reasoning_trace}
                </pre>
              )}
            </>)}
          </>) : <p style={{ opacity: 0.6 }}>Select a session.</p>}
        </div>
      </div>
      <footer style={{ marginTop: 32, fontSize: 12, opacity: 0.5 }}>
        triage4-sport · sibling-level dashboard · MIT license
      </footer>
    </div>
  );
}
