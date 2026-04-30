import { useEffect, useState } from "react";
import { api } from "./api";
import type { Recommendation, Report, SubmissionDetail } from "./types";

const REC_COLOR: Record<Recommendation, string> = {
  can_wait: "#27ae60", routine_visit: "#e6a23c", see_today: "#e74c3c",
};
const REC_LABEL: Record<Recommendation, string> = {
  can_wait: "Can wait", routine_visit: "Routine visit", see_today: "See today",
};

function Bar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = pct < 45 ? "#e74c3c" : pct < 65 ? "#e6a23c" : "#27ae60";
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span style={{ opacity: 0.85 }}>{label}</span><span>{value.toFixed(2)}</span>
      </div>
      <div style={{ height: 6, background: "#33223a", borderRadius: 3, overflow: "hidden" }}>
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
      if (!selected && d.submissions.length) setSelected(d.submissions[0].pet_token); }
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
      <p>Backend running? <code>uvicorn triage4_pet.ui.dashboard_api:app</code></p>
    </div>
  );
  if (!report) return <div style={{ padding: 24 }}>Loading…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <header style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>triage4-pet</h1>
        <span style={{ opacity: 0.7 }}>{report.submission_count} owner submissions</span>
        <button onClick={reload} style={{ marginLeft: "auto", padding: "6px 14px",
          background: "#7d3a8a", color: "white", border: 0, borderRadius: 4, cursor: "pointer" }}>
          Re-seed demo
        </button>
      </header>
      <section style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        {(["can_wait", "routine_visit", "see_today"] as const).map((r) => (
          <div key={r} style={{ flex: 1, minWidth: 160, background: "#241830",
            padding: 12, borderRadius: 6, borderLeft: `4px solid ${REC_COLOR[r]}` }}>
            <div style={{ fontSize: 12, opacity: 0.7, textTransform: "uppercase" }}>{REC_LABEL[r]}</div>
            <div style={{ fontSize: 28, fontWeight: 600 }}>{report.recommendation_counts[r]}</div>
          </div>
        ))}
      </section>
      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <div style={{ background: "#241830", borderRadius: 6, padding: 8, maxHeight: 600, overflowY: "auto" }}>
          {report.submissions.map((s) => (
            <button key={s.pet_token} onClick={() => setSelected(s.pet_token)}
              style={{ display: "block", width: "100%", textAlign: "left", padding: "8px 12px",
                margin: "2px 0", background: selected === s.pet_token ? "#33223a" : "transparent",
                color: "#e8dcef", border: 0, borderLeft: `4px solid ${REC_COLOR[s.assessment.recommendation]}`,
                borderRadius: 4, cursor: "pointer", fontSize: 13 }}>
              <div style={{ fontWeight: 600 }}>{s.pet_token}</div>
              <div style={{ fontSize: 11, opacity: 0.75 }}>
                {REC_LABEL[s.assessment.recommendation]} · overall {s.assessment.overall.toFixed(2)}
              </div>
            </button>
          ))}
        </div>
        <div style={{ background: "#241830", borderRadius: 6, padding: 16, minHeight: 300 }}>
          {detail ? (<>
            <h2 style={{ marginTop: 0, fontSize: 18 }}>
              {detail.pet_token}{" "}
              <span style={{ fontSize: 12, padding: "2px 8px", borderRadius: 3,
                background: REC_COLOR[detail.assessment.recommendation], marginLeft: 8 }}>
                {REC_LABEL[detail.assessment.recommendation]}
              </span>
            </h2>
            {detail.species && (
              <p style={{ opacity: 0.85 }}>
                <b>{detail.species}</b>{detail.age_years !== null ? `, ${detail.age_years} yr` : ""}
              </p>
            )}
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Channels</h3>
            <Bar value={detail.assessment.gait_safety} label="Gait" />
            <Bar value={detail.assessment.respiratory_safety} label="Respiratory" />
            <Bar value={detail.assessment.cardiac_safety} label="Cardiac" />
            <Bar value={detail.assessment.pain_safety} label="Pain indicator" />
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Owner messages ({detail.owner_messages.length})</h3>
            <ul style={{ paddingLeft: 18 }}>
              {detail.owner_messages.map((m, i) => <li key={i}>{m.text}</li>)}
            </ul>
            <h3 style={{ fontSize: 14, marginTop: 16 }}>Vet summary</h3>
            <pre style={{ whiteSpace: "pre-wrap", background: "#1a1124",
              padding: 12, borderRadius: 4, fontSize: 12, lineHeight: 1.5 }}>
              {detail.vet_summary}
            </pre>
          </>) : <p style={{ opacity: 0.6 }}>Select a submission.</p>}
        </div>
      </div>
      <footer style={{ marginTop: 32, fontSize: 12, opacity: 0.5 }}>
        triage4-pet · sibling-level dashboard · MIT license
      </footer>
    </div>
  );
}
