// Adapted from svend4/in4n — 2-react/src/components/SemanticZoom.jsx.
// Original copyright (c) svend4. See triage4/third_party/ATTRIBUTION.md.
//
// Upstream popup showed a knowledge-graph node description; triage4 reuses
// the same fade-by-distance card to show a casualty's triage state when the
// operator hovers over their marker on the tactical map.

import type { MapCasualty } from "../types";
import { priorityColor } from "../util/priority";

type NearCasualty = MapCasualty & { px: number; py: number; distToCamera: number };

export default function SemanticZoom({ near }: { near: NearCasualty | null }) {
  if (!near) return null;

  const color = priorityColor(near.priority);
  const alpha = Math.min(1, Math.max(0, 1 - near.distToCamera / 120));

  return (
    <div
      style={{
        position: "absolute",
        left: near.px + 20,
        top: near.py - 40,
        pointerEvents: "none",
        opacity: alpha,
        transition: "opacity 0.2s",
        zIndex: 20
      }}
    >
      <div
        style={{
          background: "rgba(7,7,20,0.88)",
          border: `1px solid ${color}55`,
          borderRadius: 8,
          padding: "10px 14px",
          minWidth: 160,
          maxWidth: 240,
          boxShadow: `0 0 24px ${color}33`,
          backdropFilter: "blur(8px)"
        }}
      >
        <div
          style={{
            fontSize: 15,
            fontWeight: "bold",
            color,
            textShadow: `0 0 12px ${color}88`,
            marginBottom: 5
          }}
        >
          {near.id}
        </div>

        <div style={{ marginBottom: 6 }}>
          <div
            style={{ fontSize: 9, opacity: 0.4, letterSpacing: 2, marginBottom: 3 }}
          >
            PRIORITY
          </div>
          <div style={{ fontSize: 12, color, textTransform: "uppercase" }}>
            {near.priority}
          </div>
        </div>

        <div style={{ fontSize: 11, color: "#aac", lineHeight: 1.5, opacity: 0.8 }}>
          confidence: {near.confidence.toFixed(2)}
        </div>
      </div>

      <div
        style={{
          width: 0,
          height: 0,
          borderTop: `6px solid ${color}44`,
          borderRight: "6px solid transparent",
          marginLeft: 8
        }}
      />
    </div>
  );
}
