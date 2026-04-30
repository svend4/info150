import { useEffect, useState } from "react";
import { api } from "./api";
import type { Recommendation, Report, SubmissionDetail } from "./types";

const REC_COLOR: Record<Recommendation, string> = {
  self_care: "#27ae60", schedule: "#e6a23c", urgent_review: "#e74c3c",
};
const REC_LABEL: Record<Recommendation, string> = {
  self_care: "Self-care", schedule: "Schedule", urgent_review: "Urgent review",
};

function Bar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = pct < 45 ? "#e74c3c" : pct < 65 ? "#e6a23c" : "#27ae60";
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span style={{ opacity: 0.85 }}>{label}</span><span>{value.toFixed(2)}</span>
      </div>
      <div style={{ height: 6, background: "#1f2c3a", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, background: color, height: "100%" }} />
      </div>
    </div>
  );
}

export default function App() {
  const [report, setReport] = useState<Report | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<SubmissionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try { setError(null); const d = await api.report(); setReport(d);
      if (!selected && d.submissions.length) setSelected(d.submissions[0].patient_token); }
    catch (e) { setError((e as Error).message); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!selected) return;
    api.submission(selected).then(setDetail).catch((e) => setError((e as Error).message));
  }, [selected]);

  const reload = async () => { await api.reload(); setSelected(null); setDetail(null); await load(); };

  if (error) return (
    <div style={{ padding: 24, color: "#ff8c8c" }}>
      Error: <code>{error}</code>
      <p>Backend running? <code>uvicorn triage4_clinic.ui.dashboard_api:app</code></p>
    </div>
  );
  if (!report) return <div style={{ padding: 24 }}>Loading…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>triage4-clinic</h1>
        <span style={{ opacity: 0.7 }}>{report.submission_count} self-report submissions</span>
        <button onClick={reload} style={{ marginLeft: "auto", padding: "6px 14px",
          background: "#1f5fbf", color: "white", border: 0, borderRadius: 4, cursor: "pointer" }}>
          Re-seed demo
        </button>
      </header>
      <section style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        {(["self_care", "schedule", "urgent_review"] as const).map((r) => (
          <div key={r} style={{ flex: 1, minWidth: 160, background: "#172430",
            padding: 12, borderRadius: 6, borderLeft: `4px solid ${REC_COLOR[r]}` }}>
            <div style={{ fontSize: 12, opacity: 0.7, textTransform: "uppercase" }}>{REC_LABEL[r]}</div>
            <div style={{ fontSize: 28, fontWeight: 600 }}>{report.recommendation_counts[r]}</div>
          </div>
        ))}
      </section>
      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <div style={{ background: "#172430", borderRadius: 6, padding: 8, maxHeight: 600, overflowY: "auto" }}>
          {report.submissions.map((s) => (
            <button key={s.patient_token} onClick={() => setSelected(s.patient_token)}
              style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px",
                margin: "2px 0", background: selected === s.patient_token ? "#1f2c3a" : "transparent",
                color: "#e0e9ef", border: 0, borderLeft: `4px solid ${REC_COLOR[s.assessment.recommendation]}`,
                borderRadius: 4, cursor: "pointer", fontSize: 13 }}>
              <div style={{ fontWeight: 600 }}>{s.patient_token}</div>
              <div style={{ fontSize: 11, opacity: 0.75 }}>
                {REC_LABEL[s.assessment.recommendation]} · {s.alert_count} alerts
              </div>
            </button>
          ))}
        </div>
        <div style={{ background: "#172430", borderRadius: 6, padding: 16, minHeight: 300 }}>
          {detail ? (<>
            <h2 style={{ marginTop: 0, fontSize: 18 }}>
              {detail.patient_token}{" "}
              <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 3,
                background: REC_COLOR[detail.assessment.recommendation], marginLeft: 8 }}>
                {REC_LABEL[detail.assessment.recommendation]}
              </span>
            </h2>
            {detail.reported_symptoms.length > 0 && (
              <p style={{ opacity: 0.85 }}>
                <b>Symptoms:</b> {detail.reported_symptoms.join(", ")}
              </p>
            )}
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Channels</h3>
            <Bar value={detail.assessment.cardiac_safety} label="Cardiac" />
            <Bar value={detail.assessment.respiratory_safety} label="Respiratory" />
            <Bar value={detail.assessment.acoustic_safety} label="Acoustic" />
            <Bar value={detail.assessment.postural_safety} label="Postural" />
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Clinician alerts ({detail.alerts.length})</h3>
            {detail.alerts.length === 0 ? <p style={{ opacity: 0.6 }}><i>none</i></p> : (
              <ul style={{ paddingLeft: 18 }}>
                {detail.alerts.map((a, i) => (
                  <li key={i} style={{ marginBottom: 8 }}>
                    <span style={{ color: REC_COLOR[a.recommendation], fontWeight: 600,
                      textTransform: "uppercase", marginRight: 6 }}>
                      {REC_LABEL[a.recommendation]}
                    </span>
                    <code>{a.channel}</code> {a.text}
                  </li>
                ))}
              </ul>
            )}
          </>) : <p style={{ opacity: 0.6 }}>Select a submission.</p>}
        </div>
      </div>
      <footer style={{ marginTop: 32, fontSize: 12, opacity: 0.5 }}>
        triage4-clinic · sibling-level dashboard · MIT license
      </footer>
    </div>
  );
}
