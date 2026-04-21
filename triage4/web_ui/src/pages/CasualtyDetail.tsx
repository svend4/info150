import type { Casualty } from "../types";
import { priorityColor } from "../util/priority";

export default function CasualtyDetail({ selected }: { selected: Casualty | null }) {
  if (!selected) return <div>Loading…</div>;

  return (
    <>
      <h1 style={{ marginTop: 0 }}>{selected.id}</h1>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <section style={{ background: "#0e1528", padding: 16, borderRadius: 12 }}>
          <h3>Overview</h3>
          <div>
            Priority:{" "}
            <b style={{ color: priorityColor(selected.triage_priority) }}>
              {selected.triage_priority}
            </b>
          </div>
          <div>Confidence: {selected.confidence}</div>
          <div>Platform: {selected.platform_source}</div>
          <div>
            Location: ({selected.location.x}, {selected.location.y}, {selected.location.z})
          </div>
        </section>

        <section style={{ background: "#0e1528", padding: 16, borderRadius: 12 }}>
          <h3>Signals</h3>
          <div>Bleeding score: {selected.signatures.bleeding_visual_score}</div>
          <div>Perfusion drop: {selected.signatures.perfusion_drop_score}</div>
          <div>Chest motion FD: {selected.signatures.chest_motion_fd}</div>
          <div>
            Respiration proxy: {selected.signatures.raw_features?.respiration_proxy ?? "—"}
          </div>
        </section>

        <section style={{ background: "#0e1528", padding: 16, borderRadius: 12 }}>
          <h3>Body Regions</h3>
          <div style={{ fontSize: 13, opacity: 0.9 }}>
            {selected.signatures.body_region_polygons
              ? Object.keys(selected.signatures.body_region_polygons).join(", ")
              : "No polygons"}
          </div>
        </section>

        <section style={{ background: "#0e1528", padding: 16, borderRadius: 12 }}>
          <h3>Hypotheses</h3>
          {selected.hypotheses.length === 0 ? (
            <div style={{ opacity: 0.7 }}>No active hypotheses</div>
          ) : (
            selected.hypotheses.map((h, idx) => (
              <div
                key={idx}
                style={{ marginBottom: 10, padding: 10, background: "#121a30", borderRadius: 8 }}
              >
                <div>
                  <b>{h.kind}</b> — {h.score}
                </div>
                <div style={{ opacity: 0.8 }}>{h.explanation}</div>
              </div>
            ))
          )}
        </section>
      </div>
    </>
  );
}
