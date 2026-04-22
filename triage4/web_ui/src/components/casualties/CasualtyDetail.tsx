// Casualty detail pane with three sub-tabs: Overview / Explain /
// Handoff. Each sub-panel fetches its own data on demand.

import { useState } from "react";

import type { Casualty } from "../../types";
import CasualtyOverview from "./CasualtyOverview";
import ConflictPanel from "./ConflictPanel";
import ExplainPanel from "./ExplainPanel";
import HandoffPanel from "./HandoffPanel";
import SecondOpinionPanel from "./SecondOpinionPanel";
import TwinPanel from "./TwinPanel";
import UncertaintyPanel from "./UncertaintyPanel";

type SubTab =
  | "overview"
  | "explain"
  | "twin"
  | "review"
  | "uncertainty"
  | "conflict"
  | "handoff";

const TABS: { key: SubTab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "explain", label: "Explain" },
  { key: "twin", label: "Twin" },
  { key: "review", label: "Review" },
  { key: "uncertainty", label: "Uncertainty" },
  { key: "conflict", label: "Conflict" },
  { key: "handoff", label: "Handoff" },
];

type Props = { casualty: Casualty | null };

export default function CasualtyDetail({ casualty }: Props) {
  const [sub, setSub] = useState<SubTab>("overview");

  if (!casualty)
    return (
      <div
        style={{
          padding: 32,
          color: "var(--text-2)",
          textAlign: "center",
          fontStyle: "italic",
        }}
      >
        select a casualty from the list on the left
      </div>
    );

  return (
    <div
      style={{
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r2)",
        overflow: "hidden",
        background: "var(--bg-1)",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: 2,
          padding: "8px 10px",
          background: "var(--bg-2)",
          borderBottom: "1px solid var(--border-1)",
        }}
      >
        {TABS.map((t) => (
          <button
            key={t.key}
            aria-pressed={sub === t.key}
            onClick={() => setSub(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div style={{ background: "var(--bg-0)" }}>
        {sub === "overview" && <CasualtyOverview casualty={casualty} />}
        {sub === "explain" && <ExplainPanel casualtyId={casualty.id} />}
        {sub === "twin" && <TwinPanel casualtyId={casualty.id} />}
        {sub === "review" && <SecondOpinionPanel casualtyId={casualty.id} />}
        {sub === "uncertainty" && <UncertaintyPanel casualtyId={casualty.id} />}
        {sub === "conflict" && <ConflictPanel casualtyId={casualty.id} />}
        {sub === "handoff" && <HandoffPanel casualtyId={casualty.id} />}
      </div>
    </div>
  );
}
