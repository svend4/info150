// Map tab: fetches /map and renders a pannable / zoomable tactical
// view with a legend and per-casualty selection.

import { useState } from "react";

import { fetchMap } from "../api/endpoints";
import MapLegend from "../components/map/MapLegend";
import TacticalMap from "../components/map/TacticalMap";
import { useResource } from "../hooks/useResource";

export default function MapPage() {
  const { data, error, loading, refresh } = useResource(fetchMap);
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <section style={{ maxWidth: 1100, margin: "0 auto" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 16,
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Tactical map</h1>
          <div
            style={{ color: "var(--text-2)", fontSize: 12, marginTop: 4 }}
          >
            Platforms (triangles) and casualties (circles) in map-frame
            coordinates.
          </div>
        </div>
        <button onClick={refresh} disabled={loading}>
          refresh
        </button>
      </header>

      {error && (
        <div
          style={{
            padding: 12,
            border: "1px solid var(--err)",
            borderRadius: "var(--r2)",
            color: "var(--err)",
            marginBottom: 16,
          }}
        >
          {error.message}
        </div>
      )}

      <div style={{ marginBottom: 12 }}>
        <MapLegend />
      </div>

      {data ? (
        <>
          <TacticalMap
            platforms={data.platforms}
            casualties={data.casualties}
            selectedCasualtyId={selected}
            onCasualtyClick={(id) =>
              setSelected((cur) => (cur === id ? null : id))
            }
          />
          {selected && (
            <div
              style={{
                marginTop: 10,
                padding: 10,
                background: "var(--bg-1)",
                border: "1px solid var(--border-1)",
                borderRadius: "var(--r2)",
                fontSize: 12,
                fontFamily: "var(--font-mono)",
              }}
            >
              selected casualty: <strong>{selected}</strong>
            </div>
          )}
        </>
      ) : (
        <div style={{ color: "var(--text-2)", fontStyle: "italic" }}>
          loading map…
        </div>
      )}
    </section>
  );
}
