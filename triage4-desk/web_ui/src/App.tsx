import { useEffect, useState } from "react";
import { api } from "./api";
import CameraPanel from "./CameraPanel";
import ThemeToggle from "./ThemeToggle";
import type { Cue, CueSeverity, PostureAdvisory, Report } from "./types";

const SEV_COLOR: Record<CueSeverity, string> = {
  ok: "#27ae60", minor: "#e6a23c", severe: "#e74c3c",
};
const POSTURE_COLOR: Record<PostureAdvisory, string> = {
  ok: "#27ae60", leaning: "#e6a23c", slumped: "#e74c3c",
};

function Bar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = pct > 70 ? "#27ae60" : pct > 40 ? "#e6a23c" : "#e74c3c";
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span style={{ opacity: 0.85 }}>{label}</span><span>{value.toFixed(2)}</span>
      </div>
      <div style={{ height: 6, background: "var(--surface-2)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, background: color, height: "100%" }} />
      </div>
    </div>
  );
}

function Flag({ on, label }: { on: boolean; label: string }) {
  return (
    <div style={{
      padding: "4px 10px", borderRadius: 4, fontSize: 12,
      background: on ? "var(--danger-bg)" : "var(--success-bg)",
      border: `1px solid ${on ? "var(--warn)" : "var(--success-strong)"}`,
      color: "var(--text)",
    }}>
      {label}: <b>{on ? "yes" : "no"}</b>
    </div>
  );
}

export default function App() {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try { setError(null); setReport(await api.report()); }
    catch (e) { setError((e as Error).message); }
  };
  useEffect(() => { load(); }, []);
  const reload = async () => { await api.reload(); await load(); };

  if (error) return (
    <div style={{ padding: 24, color: "var(--danger-text)" }}>
      Error: <code>{error}</code>
      <p>Backend running? <code>uvicorn triage4_desk.ui.dashboard_api:app</code></p>
    </div>
  );
  if (!report) return <div style={{ padding: 24 }}>Loading…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16, flexWrap: "wrap" }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>triage4-desk</h1>
        <span style={{ opacity: 0.7 }}>
          {report.worker_id} · {report.work_mode} · session {report.session_min.toFixed(0)} min
          · break {report.minutes_since_break.toFixed(0)} min ago
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          <ThemeToggle />
          <button onClick={reload} style={{ padding: "6px 14px",
            background: "var(--success-strong)", color: "#fff", border: 0,
            borderRadius: 4, cursor: "pointer" }}>
            Re-seed demo
          </button>
        </div>
      </header>
      <CameraPanel onAnalyzed={load} />
      <section style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        {(["ok", "minor", "severe"] as const).map((s) => (
          <div key={s} style={{ flex: 1, minWidth: 160, background: "var(--surface)",
            padding: 12, borderRadius: 6, borderLeft: `4px solid ${SEV_COLOR[s]}` }}>
            <div style={{ fontSize: 12, opacity: 0.7, textTransform: "uppercase" }}>{s}</div>
            <div style={{ fontSize: 28, fontWeight: 600 }}>{report.severity_counts[s]}</div>
          </div>
        ))}
      </section>
      <section style={{ background: "var(--surface)", borderRadius: 6, padding: 16, marginBottom: 16 }}>
        <h3 style={{ marginTop: 0, fontSize: 14 }}>Channels</h3>
        <Bar value={report.overall_safety} label="Overall safety" />
        <Bar value={1.0 - report.fatigue_index} label="Reserve (1 − fatigue)" />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
          <Flag on={report.hydration_due} label="hydration_due" />
          <Flag on={report.eye_break_due} label="eye_break_due (20-20-20)" />
          <Flag on={report.microbreak_due} label="microbreak_due (Pomodoro)" />
          <Flag on={report.stretch_due} label="stretch_due" />
          <Flag on={report.drowsiness_alert} label="drowsiness" />
          <Flag on={report.distraction_alert} label="distraction" />
          <div style={{ padding: "4px 10px", borderRadius: 4, fontSize: 12,
            background: "var(--surface-2)",
            border: `1px solid ${POSTURE_COLOR[report.posture_advisory]}`,
            color: "var(--text)" }}>
            posture: <b style={{ color: POSTURE_COLOR[report.posture_advisory] }}>
              {report.posture_advisory}
            </b>
          </div>
        </div>
      </section>
      <section style={{ background: "var(--surface)", borderRadius: 6, padding: 16 }}>
        <h3 style={{ marginTop: 0, fontSize: 14 }}>Coaching cues ({report.cues.length})</h3>
        {report.cues.length === 0
          ? <p style={{ opacity: 0.6 }}><i>none — keep working comfortably.</i></p>
          : (
            <ul style={{ paddingLeft: 18 }}>
              {report.cues.map((c: Cue, i: number) => (
                <li key={i}>
                  <span style={{ color: SEV_COLOR[c.severity], fontWeight: 600,
                    textTransform: "uppercase", marginRight: 6 }}>{c.severity}</span>
                  <code>{c.kind}</code>&nbsp;{c.text}
                </li>
              ))}
            </ul>
          )}
      </section>
      <footer style={{ marginTop: 32, fontSize: 12, opacity: 0.5 }}>
        triage4-desk · Pomodoro / 20-20-20 / posture / drowsiness · MIT
      </footer>
    </div>
  );
}
