import { useEffect, useState } from "react";
import { api } from "./api";
import type { Casualty, Cue, Incident } from "./types";

const TAG_COLOR: Record<string, string> = {
  immediate: "#e74c3c",
  delayed: "#e6a23c",
  minor: "#27ae60",
  deceased: "#444",
};

export default function App() {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] =
    useState<(Casualty & { cues: Cue[] }) | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setError(null);
      const data = await api.incident();
      setIncident(data);
      if (!selected && data.assessments.length > 0) {
        setSelected(data.assessments[0].casualty_id);
      }
    } catch (e) {
      setError((e as Error).message);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!selected) return;
    api
      .casualty(selected)
      .then(setSelectedDetail)
      .catch((e) => setError((e as Error).message));
  }, [selected]);

  const reload = async () => {
    await api.reload();
    setSelected(null);
    setSelectedDetail(null);
    await load();
  };

  if (error)
    return (
      <div style={{ padding: 24, color: "#ff8c8c" }}>
        Error talking to triage4-rescue API: <code>{error}</code>
        <p>
          Is the FastAPI backend running on
          <code> http://127.0.0.1:8000</code>? Try{" "}
          <code>uvicorn triage4_rescue.ui.dashboard_api:app</code>.
        </p>
      </div>
    );

  if (!incident) return <div style={{ padding: 24 }}>Loading…</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          marginBottom: 16,
        }}
      >
        <h1 style={{ margin: 0, fontSize: 22 }}>triage4-rescue</h1>
        <span style={{ opacity: 0.7 }}>
          incident <code>{incident.incident_id}</code> · {incident.casualty_count}{" "}
          casualties
        </span>
        <button
          onClick={reload}
          style={{
            marginLeft: "auto",
            padding: "6px 14px",
            background: "#1f5fbf",
            color: "white",
            border: 0,
            borderRadius: 4,
            cursor: "pointer",
          }}
        >
          Re-seed demo
        </button>
      </header>

      <section
        style={{
          display: "flex",
          gap: 12,
          marginBottom: 24,
          flexWrap: "wrap",
        }}
      >
        {(["immediate", "delayed", "minor", "deceased"] as const).map((t) => (
          <div
            key={t}
            style={{
              flex: 1,
              minWidth: 140,
              background: "#1c2336",
              padding: 12,
              borderRadius: 6,
              borderLeft: `4px solid ${TAG_COLOR[t]}`,
            }}
          >
            <div style={{ fontSize: 12, opacity: 0.7, textTransform: "uppercase" }}>
              {t}
            </div>
            <div style={{ fontSize: 28, fontWeight: 600 }}>{incident.counts[t]}</div>
          </div>
        ))}
      </section>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <div
          style={{
            background: "#1c2336",
            borderRadius: 6,
            padding: 8,
            maxHeight: 600,
            overflowY: "auto",
          }}
        >
          {incident.assessments.map((a) => (
            <button
              key={a.casualty_id}
              onClick={() => setSelected(a.casualty_id)}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "8px 12px",
                margin: "2px 0",
                background:
                  selected === a.casualty_id ? "#2d3a5c" : "transparent",
                color: "#e7eaf2",
                border: 0,
                borderLeft: `4px solid ${TAG_COLOR[a.tag]}`,
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              <div style={{ fontWeight: 600 }}>
                {a.casualty_id}
                {a.flag_for_secondary_review ? " ⚐" : ""}
              </div>
              <div style={{ fontSize: 11, opacity: 0.75 }}>
                {a.tag} · {a.age_group}
              </div>
            </button>
          ))}
        </div>

        <div
          style={{ background: "#1c2336", borderRadius: 6, padding: 16, minHeight: 300 }}
        >
          {selectedDetail ? (
            <>
              <h2 style={{ marginTop: 0, fontSize: 18 }}>
                {selectedDetail.casualty_id}{" "}
                <span
                  style={{
                    fontSize: 12,
                    padding: "2px 8px",
                    borderRadius: 3,
                    background: TAG_COLOR[selectedDetail.tag],
                    marginLeft: 8,
                  }}
                >
                  {selectedDetail.tag}
                </span>
              </h2>
              <p style={{ opacity: 0.85 }}>
                <b>Age group:</b> {selectedDetail.age_group}
                {selectedDetail.flag_for_secondary_review && (
                  <span style={{ color: "#e6a23c", marginLeft: 12 }}>
                    flagged for secondary review
                  </span>
                )}
              </p>
              <p>
                <b>Reasoning:</b> {selectedDetail.reasoning}
              </p>
              <h3 style={{ fontSize: 14, marginTop: 16 }}>
                Responder cues ({selectedDetail.cues.length})
              </h3>
              {selectedDetail.cues.length === 0 ? (
                <p style={{ opacity: 0.6 }}>
                  <i>none</i>
                </p>
              ) : (
                <ul style={{ paddingLeft: 18 }}>
                  {selectedDetail.cues.map((c, i) => (
                    <li key={i}>
                      <code>{c.kind}</code> [{c.severity}] {c.text}
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p style={{ opacity: 0.6 }}>Select a casualty to see detail.</p>
          )}
        </div>
      </div>

      <footer style={{ marginTop: 32, fontSize: 12, opacity: 0.5 }}>
        triage4-rescue · sibling-level dashboard · MIT license
      </footer>
    </div>
  );
}
