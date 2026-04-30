import { useEffect, useState } from "react";
import { api } from "./api";
import type { Alert, Report, Score, WelfareFlag } from "./types";

const FLAG_COLOR: Record<WelfareFlag, string> = {
  well: "#27ae60", concern: "#e6a23c", urgent: "#e74c3c",
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
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<(Score & { alerts: Alert[] }) | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try { setError(null); const d = await api.report(); setReport(d);
      if (!selected && d.scores.length) setSelected(d.scores[0].animal_id); }
    catch (e) { setError((e as Error).message); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!selected) return;
    api.animal(selected).then(setDetail).catch((e) => setError((e as Error).message));
  }, [selected]);

  const reload = async () => { await api.reload(); setSelected(null); setDetail(null); await load(); };

  if (error) return (
    <div style={{ padding: 24, color: "#ff8c8c" }}>
      Error: <code>{error}</code>
      <p>Backend running? <code>uvicorn triage4_farm.ui.dashboard_api:app</code></p>
    </div>
  );
  if (!report) return <div style={{ padding: 24 }}>Loading…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>triage4-farm</h1>
        <span style={{ opacity: 0.7 }}>
          farm <code>{report.farm_id}</code> · {report.animal_count} animals · herd overall {report.herd_overall.toFixed(2)}
        </span>
        <button onClick={reload} style={{ marginLeft: "auto", padding: "6px 14px",
          background: "#3a8443", color: "white", border: 0, borderRadius: 4, cursor: "pointer" }}>
          Re-seed demo
        </button>
      </header>
      <section style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        {(["well", "concern", "urgent"] as const).map((f) => (
          <div key={f} style={{ flex: 1, minWidth: 160, background: "#16241b",
            padding: 12, borderRadius: 6, borderLeft: `4px solid ${FLAG_COLOR[f]}` }}>
            <div style={{ fontSize: 12, opacity: 0.7, textTransform: "uppercase" }}>{f}</div>
            <div style={{ fontSize: 28, fontWeight: 600 }}>{report.flag_counts[f]}</div>
          </div>
        ))}
      </section>
      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <div style={{ background: "#16241b", borderRadius: 6, padding: 8, maxHeight: 600, overflowY: "auto" }}>
          {report.scores.map((s) => (
            <button key={s.animal_id} onClick={() => setSelected(s.animal_id)}
              style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px",
                margin: "2px 0", background: selected === s.animal_id ? "#22332a" : "transparent",
                color: "#dde7df", border: 0, borderLeft: `4px solid ${FLAG_COLOR[s.flag]}`,
                borderRadius: 4, cursor: "pointer", fontSize: 13 }}>
              <div style={{ fontWeight: 600 }}>{s.animal_id}</div>
              <div style={{ fontSize: 11, opacity: 0.75 }}>
                {s.flag} · overall {s.overall.toFixed(2)}
              </div>
            </button>
          ))}
        </div>
        <div style={{ background: "#16241b", borderRadius: 6, padding: 16, minHeight: 300 }}>
          {detail ? (<>
            <h2 style={{ marginTop: 0, fontSize: 18 }}>
              {detail.animal_id}{" "}
              <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 3,
                background: FLAG_COLOR[detail.flag], marginLeft: 8 }}>
                {detail.flag}
              </span>
            </h2>
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Channels</h3>
            <Bar value={detail.gait} label="Gait" />
            <Bar value={detail.respiratory} label="Respiratory" />
            <Bar value={detail.thermal} label="Thermal" />
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Alerts ({detail.alerts.length})</h3>
            {detail.alerts.length === 0 ? <p style={{ opacity: 0.6 }}><i>none</i></p> : (
              <ul style={{ paddingLeft: 18 }}>
                {detail.alerts.map((a, i) => (
                  <li key={i}>
                    <span style={{ color: FLAG_COLOR[a.flag], fontWeight: 600,
                      textTransform: "uppercase", marginRight: 6 }}>{a.flag}</span>
                    <code>{a.kind}</code> {a.text}
                  </li>
                ))}
              </ul>
            )}
          </>) : <p style={{ opacity: 0.6 }}>Select an animal to see channels + alerts.</p>}
        </div>
      </div>
      <footer style={{ marginTop: 32, fontSize: 12, opacity: 0.5 }}>
        triage4-farm · sibling-level dashboard · MIT license
      </footer>
    </div>
  );
}
