// Adapted from svend4/in4n — 2-react/src/components/InfoPanel.jsx.
// Original copyright (c) svend4. See triage4/third_party/ATTRIBUTION.md.
//
// Upstream panel showed current/target knowledge-graph node + time era;
// triage4 reuses the frame to show current casualty, medic handoff target,
// mission replay frame and operator hints.

import type { Casualty } from "../types";
import { priorityColor } from "../util/priority";

type Props = {
  current: Casualty | null;
  handoffTarget: string | null;
  frame: number;
  maxFrame: number;
  onFrameChange: (n: number) => void;
};

export default function InfoPanel({
  current,
  handoffTarget,
  frame,
  maxFrame,
  onFrameChange
}: Props) {
  const color = current ? priorityColor(current.triage_priority) : "#4fc3f7";

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none"
      }}
    >
      <div style={{ position: "absolute", top: 24, left: 24 }}>
        <div
          style={{
            fontSize: 10,
            letterSpacing: 3,
            opacity: 0.35,
            textTransform: "uppercase"
          }}
        >
          triage4
        </div>
        <div
          style={{
            marginTop: 8,
            fontSize: 28,
            fontWeight: "bold",
            color,
            textShadow: `0 0 24px ${color}88`,
            minHeight: 36
          }}
        >
          {current?.id ?? "…"}
        </div>
        {current && (
          <div
            style={{ marginTop: 4, fontSize: 11, opacity: 0.5, color: "#ccc" }}
          >
            {current.triage_priority} / conf {current.confidence.toFixed(2)}
          </div>
        )}
        {handoffTarget && (
          <div style={{ marginTop: 6, fontSize: 11, color: "#ffd54f", opacity: 0.8 }}>
            ⟶ handoff: {handoffTarget}
          </div>
        )}
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 32,
          left: "50%",
          transform: "translateX(-50%)",
          textAlign: "center",
          pointerEvents: "all"
        }}
      >
        <div
          style={{
            fontSize: 10,
            opacity: 0.4,
            marginBottom: 6,
            letterSpacing: 2
          }}
        >
          MISSION TIMELINE
        </div>
        <input
          type="range"
          min={0}
          max={Math.max(maxFrame, 1)}
          step={1}
          value={frame}
          onChange={(e) => onFrameChange(+e.target.value)}
          style={{ width: 260, accentColor: "#4fc3f7", cursor: "pointer" }}
        />
        <div style={{ marginTop: 4, fontSize: 13, color: "#4fc3f7", opacity: 0.8 }}>
          Frame {frame} / {maxFrame}
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 24,
          right: 24,
          fontSize: 10,
          opacity: 0.25,
          textAlign: "right",
          lineHeight: 2
        }}
      >
        Click — select casualty
        <br />
        Slider — replay frame
        <br />
        Tabs — casualties / map / replay
      </div>
    </div>
  );
}
