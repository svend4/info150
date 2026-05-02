import { useEffect, useState } from "react";
import { api } from "./api";
import CameraPanel from "./CameraPanel";
import type { FarmAlert, FarmReport, PenScore } from "./types";

const LEVEL_COLOR: Record<string, string> = {
  steady: "#27ae60",
  watch: "#e6a23c",
  urgent: "#e74c3c",
};

function ScoreBar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value * 100));
  const color = pct < 45 ? "#e74c3c" : pct < 65 ? "#e6a23c" : "#27ae60";
  return (
    <div style={{ marginBottom: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
        <span style={{ opacity: 0.85 }}>{label}</span>
        <span>{value.toFixed(2)}</span>
      </div>
      <div
        style={{
          height: 6,
          background: "#2a3346",
          borderRadius: 3,
          overflow: "hidden",
        }}
      >
        <div style={{ width: `${pct}%`, background: color, height: "100%" }} />
      </div>
    </div>
  );
}

export default function App() {
  const [report, setReport] = useState<FarmReport | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [selectedDetail, setSelectedDetail] =
    useState<(PenScore & { alerts: FarmAlert[] }) | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setError(null);
      const data = await api.report();
      setReport(data);
      if (!selected && data.scores.length > 0) {
        setSelected(data.scores[0].pen_id);
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
      .pen(selected)
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
        Error talking to triage4-fish API: <code>{error}</code>
        <p>
          Is the FastAPI backend running on
          <code> http://127.0.0.1:8000</code>? Try{" "}
          <code>uvicorn triage4_fish.ui.dashboard_api:app</code>.
        </p>
      </div>
    );

  if (!report) return <div style={{ padding: 24 }}>Loading…</div>;

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
        <h1 style={{ margin: 0, fontSize: 22 }}>triage4-fish</h1>
        <span style={{ opacity: 0.7 }}>
          farm <code>{report.farm_id}</code> · {report.pen_count} pens ·{" "}
          {report.alerts.length} alerts
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
      <CameraPanel onAnalyzed={load} />

      <section
        style={{
          display: "flex",
          gap: 12,
          marginBottom: 24,
          flexWrap: "wrap",
        }}
      >
        {(["steady", "watch", "urgent"] as const).map((lvl) => (
          <div
            key={lvl}
            style={{
              flex: 1,
              minWidth: 160,
              background: "#162132",
              padding: 12,
              borderRadius: 6,
              borderLeft: `4px solid ${LEVEL_COLOR[lvl]}`,
            }}
          >
            <div style={{ fontSize: 12, opacity: 0.7, textTransform: "uppercase" }}>
              {lvl}
            </div>
            <div style={{ fontSize: 28, fontWeight: 600 }}>
              {report.level_counts[lvl]}
            </div>
          </div>
        ))}
      </section>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16 }}>
        <div
          style={{
            background: "#162132",
            borderRadius: 6,
            padding: 8,
            maxHeight: 600,
            overflowY: "auto",
          }}
        >
          {report.scores.map((s) => (
            <button
              key={s.pen_id}
              onClick={() => setSelected(s.pen_id)}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "8px 12px",
                margin: "2px 0",
                background:
                  selected === s.pen_id ? "#243250" : "transparent",
                color: "#e0eaf2",
                border: 0,
                borderLeft: `4px solid ${LEVEL_COLOR[s.welfare_level]}`,
                borderRadius: 4,
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              <div style={{ fontWeight: 600 }}>{s.pen_id}</div>
              <div style={{ fontSize: 11, opacity: 0.75 }}>
                {s.welfare_level} · overall {s.overall.toFixed(2)}
              </div>
            </button>
          ))}
        </div>

        <div
          style={{ background: "#162132", borderRadius: 6, padding: 16, minHeight: 300 }}
        >
          {selectedDetail ? (
            <>
              <h2 style={{ marginTop: 0, fontSize: 18 }}>
                {selectedDetail.pen_id}{" "}
                <span
                  style={{
                    fontSize: 12,
                    padding: "2px 8px",
                    borderRadius: 3,
                    background: LEVEL_COLOR[selectedDetail.welfare_level],
                    marginLeft: 8,
                  }}
                >
                  {selectedDetail.welfare_level}
                </span>
              </h2>
              {selectedDetail.species && (
                <p style={{ opacity: 0.85 }}>
                  <b>Species:</b> {selectedDetail.species}
                  {selectedDetail.location_handle && (
                    <span style={{ marginLeft: 12 }}>
                      <b>Location:</b> <code>{selectedDetail.location_handle}</code>
                    </span>
                  )}
                </p>
              )}
              <h3 style={{ fontSize: 14, marginTop: 16 }}>Channels</h3>
              <ScoreBar value={selectedDetail.gill_rate_safety} label="Gill rate" />
              <ScoreBar
                value={selectedDetail.school_cohesion_safety}
                label="School cohesion"
              />
              <ScoreBar value={selectedDetail.sea_lice_safety} label="Sea lice" />
              <ScoreBar
                value={selectedDetail.mortality_safety}
                label="Mortality floor"
              />
              <ScoreBar
                value={selectedDetail.water_chemistry_safety}
                label="Water chemistry"
              />
              <h3 style={{ fontSize: 14, marginTop: 16 }}>
                Alerts ({selectedDetail.alerts.length})
              </h3>
              {selectedDetail.alerts.length === 0 ? (
                <p style={{ opacity: 0.6 }}>
                  <i>none</i>
                </p>
              ) : (
                <ul style={{ paddingLeft: 18 }}>
                  {selectedDetail.alerts.map((a, i) => (
                    <li key={i}>
                      <span
                        style={{
                          color: LEVEL_COLOR[a.level],
                          fontWeight: 600,
                          textTransform: "uppercase",
                          marginRight: 6,
                        }}
                      >
                        {a.level}
                      </span>
                      <code>{a.kind}</code> {a.text}
                    </li>
                  ))}
                </ul>
              )}
            </>
          ) : (
            <p style={{ opacity: 0.6 }}>Select a pen to see channels + alerts.</p>
          )}
        </div>
      </div>

      <footer style={{ marginTop: 32, fontSize: 12, opacity: 0.5 }}>
        triage4-fish · sibling-level dashboard · MIT license
      </footer>
    </div>
  );
}
