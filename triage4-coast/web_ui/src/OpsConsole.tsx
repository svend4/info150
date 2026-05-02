// Composes the Stage 2A widgets into a single ops-console layout:
//
//   ┌────────────── SchematicMap (full width) ──────────────┐
//   │  zones laid out left → right, click to select         │
//   ├──────────── HeatStressGauge ─── RadarChart ───────────┤
//   ├────────────── TimeStripChart (24h) ───────────────────┤
//   ├────────────── StackedTrend (4h) ──────────────────────┤
//   ├──── BroadcastPanel ──────── IncidentTimeline ─────────┤

import { useState } from "react";
import BroadcastPanel from "./BroadcastPanel";
import HeatStressGauge from "./HeatStressGauge";
import IncidentTimeline from "./IncidentTimeline";
import RadarChart from "./RadarChart";
import SchematicMap from "./SchematicMap";
import StackedTrend from "./StackedTrend";
import TimeStripChart from "./TimeStripChart";
import type { Score } from "./types";

export default function OpsConsole({ scores }: { scores: Score[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(
    scores[0]?.zone_id ?? null,
  );
  const selected = scores.find((s) => s.zone_id === selectedId) ?? null;
  const zoneIds = scores.map((s) => s.zone_id);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <SchematicMap
        scores={scores}
        selected={selectedId}
        onSelect={setSelectedId}
      />

      <div style={{ display: "grid",
        gridTemplateColumns: "240px 240px 1fr", gap: 12 }}>
        <HeatStressGauge scores={scores} />
        <RadarChart score={selected} />
        <BroadcastPanel zoneIds={zoneIds} onSent={() => { /* refetched via timeline poll */ }} />
      </div>

      <TimeStripChart zoneIds={zoneIds} hours={24} />

      <StackedTrend hours={4} bucketMinutes={5} />

      <IncidentTimeline />
    </div>
  );
}
