import { useEffect, useState } from "react";
import { api } from "./api";
import CameraPanel from "./CameraPanel";
import type { Cue, CueSeverity, FormScore, Report } from "./types";

const SEV_COLOR: Record<CueSeverity, string> = {
  ok: "#27ae60", minor: "#e6a23c", severe: "#e74c3c",
};

function Bar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = pct < 45 ? "#e74c3c" : pct < 65 ? "#e6a23c" : "#27ae60";
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

export default function App() {
  const [report, setReport] = useState<Report | null>(null);
  const [selected, setSelected] = useState<number>(0);
  const [detail, setDetail] = useState<(FormScore & { cues: Cue[] }) | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try { setError(null); const d = await api.report(); setReport(d);
      if (d.form_scores.length) setSelected(d.form_scores[0].rep_index); }
    catch (e) { setError((e as Error).message); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!report) return;
    api.rep(selected).then(setDetail).catch((e) => setError((e as Error).message));
  }, [selected, report]);

  const reload = async () => { await api.reload(); setSelected(0); setDetail(null); await load(); };

  if (error) return (
    <div style={{ padding: 24, color: "#ff8c8c" }}>
      Error: <code>{error}</code>
      <p>Backend running? <code>uvicorn triage4_fit.ui.dashboard_api:app</code></p>
    </div>
  );
  if (!report) return <div style={{ padding: 24 }}>Loading…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>triage4-fit</h1>
        <span style={{ opacity: 0.7 }}>
          {report.exercise} · {report.rep_count} reps · session overall {report.session_overall.toFixed(2)}
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
      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <div style={{ background: "#16241b", borderRadius: 6, padding: 8, maxHeight: 600, overflowY: "auto" }}>
          {report.form_scores.map((s) => (
            <button key={s.rep_index} onClick={() => setSelected(s.rep_index)}
              style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px",
                margin: "2px 0", background: selected === s.rep_index ? "#22332a" : "transparent",
                color: "#dde7df", border: 0,
                borderLeft: `4px solid ${s.overall < 0.5 ? "#e74c3c" : s.overall < 0.7 ? "#e6a23c" : "#27ae60"}`,
                borderRadius: 4, cursor: "pointer", fontSize: 13 }}>
              <div style={{ fontWeight: 600 }}>Rep #{s.rep_index}</div>
              <div style={{ fontSize: 11, opacity: 0.75 }}>
                overall {s.overall.toFixed(2)}
              </div>
            </button>
          ))}
        </div>
        <div style={{ background: "#16241b", borderRadius: 6, padding: 16, minHeight: 300 }}>
          {detail ? (<>
            <h2 style={{ marginTop: 0, fontSize: 18 }}>
              Rep #{detail.rep_index}{" "}
              <span style={{ fontSize: 12, opacity: 0.75, marginLeft: 8 }}>
                overall {detail.overall.toFixed(2)}
              </span>
            </h2>
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Channels</h3>
            <Bar value={detail.symmetry} label="Symmetry" />
            <Bar value={detail.depth} label="Depth" />
            <Bar value={detail.tempo} label="Tempo" />
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Coach cues ({detail.cues.length})</h3>
            {detail.cues.length === 0 ? <p style={{ opacity: 0.6 }}><i>none</i></p> : (
              <ul style={{ paddingLeft: 18 }}>
                {detail.cues.map((c, i) => (
                  <li key={i}>
                    <span style={{ color: SEV_COLOR[c.severity], fontWeight: 600,
                      textTransform: "uppercase", marginRight: 6 }}>{c.severity}</span>
                    <code>{c.kind}</code> {c.text}
                  </li>
                ))}
              </ul>
            )}
          </>) : <p style={{ opacity: 0.6 }}>Select a rep.</p>}
        </div>
      </div>
      <footer style={{ marginTop: 32, fontSize: 12, opacity: 0.5 }}>
        triage4-fit · sibling-level dashboard · MIT license
      </footer>
    </div>
  );
}
