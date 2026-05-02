import { useEffect, useState } from "react";
import { api } from "./api";
import CameraPanel from "./CameraPanel";
import type { Cue, CueSeverity, Report } from "./types";

const SEV_COLOR: Record<CueSeverity, string> = {
  ok: "#27ae60", minor: "#e6a23c", severe: "#e74c3c",
};

function Bar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = pct > 70 ? "#27ae60" : pct > 40 ? "#e6a23c" : "#e74c3c";
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span style={{ opacity: 0.85 }}>{label}</span><span>{value.toFixed(2)}</span>
      </div>
      <div style={{ height: 6, background: "#22332a", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, background: color, height: "100%" }} />
      </div>
    </div>
  );
}

function Flag({ on, label }: { on: boolean; label: string }) {
  return (
    <div style={{
      padding: "4px 10px", borderRadius: 4, fontSize: 12,
      background: on ? "#5a3a1a" : "#1f2a22",
      border: `1px solid ${on ? "#e6a23c" : "#3a8443"}`,
      color: on ? "#ffd28c" : "#7da785",
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
    <div style={{ padding: 24, color: "#ff8c8c" }}>
      Error: <code>{error}</code>
      <p>Backend running? <code>uvicorn triage4_stroll.ui.dashboard_api:app</code></p>
    </div>
  );
  if (!report) return <div style={{ padding: 24 }}>Loading…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>triage4-stroll</h1>
        <span style={{ opacity: 0.7 }}>
          {report.walker_id} · {report.terrain} · {report.duration_min.toFixed(0)} min
          · pace {report.pace_kmh.toFixed(1)} km/h
        </span>
        <button onClick={reload} style={{ marginLeft: "auto", padding: "6px 14px",
          background: "#3a8443", color: "white", border: 0, borderRadius: 4, cursor: "pointer" }}>
          Re-seed demo
        </button>
      </header>
      <CameraPanel onAnalyzed={load} />
      <section style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        {(["ok", "minor", "severe"] as const).map((s) => (
          <div key={s} style={{ flex: 1, minWidth: 160, background: "#16241b",
            padding: 12, borderRadius: 6, borderLeft: `4px solid ${SEV_COLOR[s]}` }}>
            <div style={{ fontSize: 12, opacity: 0.7, textTransform: "uppercase" }}>{s}</div>
            <div style={{ fontSize: 28, fontWeight: 600 }}>{report.severity_counts[s]}</div>
          </div>
        ))}
      </section>
      <section style={{ background: "#16241b", borderRadius: 6, padding: 16, marginBottom: 16 }}>
        <h3 style={{ marginTop: 0, fontSize: 14 }}>Channels</h3>
        <Bar value={report.overall_safety} label="Overall safety" />
        <Bar value={1.0 - report.fatigue_index} label="Reserve (1 − fatigue)" />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
          <Flag on={report.hydration_due} label="hydration_due" />
          <Flag on={report.shade_advisory} label="shade_advisory" />
          <Flag on={report.rest_due} label="rest_due" />
          <div style={{ padding: "4px 10px", borderRadius: 4, fontSize: 12,
            background: "#1f2a22", border: "1px solid #3a8443", color: "#dde7df" }}>
            pace_advisory: <b>{report.pace_advisory}</b>
          </div>
        </div>
      </section>
      <section style={{ background: "#16241b", borderRadius: 6, padding: 16 }}>
        <h3 style={{ marginTop: 0, fontSize: 14 }}>Coaching cues ({report.cues.length})</h3>
        {report.cues.length === 0
          ? <p style={{ opacity: 0.6 }}><i>none — keep walking comfortably.</i></p>
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
        triage4-stroll · day-walk advisor · MIT license
      </footer>
    </div>
  );
}
