import { useEffect, useState } from "react";

import CasualtyDetail from "./pages/CasualtyDetail";
import MapPage from "./pages/MapPage";
import ReplayPage from "./pages/ReplayPage";
import type { Casualty, MapData, ReplayData } from "./types";
import { priorityColor } from "./util/priority";

type TabKey = "casualties" | "map" | "replay";

// Empty string = relative paths, which the Vite dev proxy (see
// web_ui/vite.config.ts) forwards to the FastAPI backend. Override
// at build / dev time with VITE_API_BASE when the frontend runs on
// a different host than the backend.
const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export default function App() {
  const [items, setItems] = useState<Casualty[]>([]);
  const [selected, setSelected] = useState<Casualty | null>(null);
  const [tab, setTab] = useState<TabKey>("casualties");
  const [mapData, setMapData] = useState<MapData | null>(null);
  const [replayData, setReplayData] = useState<ReplayData | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/casualties`)
      .then((r) => r.json())
      .then((data: Casualty[]) => {
        setItems(data);
        if (data.length > 0) setSelected(data[0]);
      });

    fetch(`${API_BASE}/map`).then((r) => r.json()).then(setMapData);
    fetch(`${API_BASE}/replay`).then((r) => r.json()).then(setReplayData);
  }, []);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", minHeight: "100vh" }}>
      <aside style={{ borderRight: "1px solid #1e2a44", padding: 16 }}>
        <h2 style={{ marginTop: 0 }}>triage4</h2>
        <div style={{ opacity: 0.8, marginBottom: 16 }}>MVP dashboard</div>

        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button onClick={() => setTab("casualties")}>Casualties</button>
          <button onClick={() => setTab("map")}>Map</button>
          <button onClick={() => setTab("replay")}>Replay</button>
        </div>

        {items.map((item) => (
          <div
            key={item.id}
            onClick={() => {
              setSelected(item);
              setTab("casualties");
            }}
            style={{
              cursor: "pointer",
              marginBottom: 12,
              padding: 12,
              borderRadius: 10,
              border: `1px solid ${priorityColor(item.triage_priority)}`,
              background: selected?.id === item.id ? "#121a30" : "#0e1528"
            }}
          >
            <div style={{ fontWeight: 700 }}>{item.id}</div>
            <div
              style={{ color: priorityColor(item.triage_priority), textTransform: "uppercase" }}
            >
              {item.triage_priority}
            </div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>confidence: {item.confidence}</div>
          </div>
        ))}
      </aside>

      <main style={{ padding: 20 }}>
        {tab === "map" && <MapPage data={mapData} />}
        {tab === "replay" && <ReplayPage data={replayData} />}
        {tab === "casualties" && <CasualtyDetail selected={selected} />}
      </main>
    </div>
  );
}
