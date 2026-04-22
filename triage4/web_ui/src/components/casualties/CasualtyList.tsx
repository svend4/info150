import type { Casualty } from "../../types";
import { priorityColor } from "../../util/priority";
import { formatConfidence } from "../../util/format";

type Props = {
  items: Casualty[];
  selectedId: string | null;
  onSelect: (casualty: Casualty) => void;
};

export default function CasualtyList({ items, selectedId, onSelect }: Props) {
  if (items.length === 0)
    return (
      <div
        style={{
          padding: 20,
          color: "var(--text-2)",
          textAlign: "center",
          fontStyle: "italic",
          fontSize: 12,
        }}
      >
        no casualties match the current filters
      </div>
    );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {items.map((c) => {
        const active = selectedId === c.id;
        return (
          <button
            key={c.id}
            onClick={() => onSelect(c)}
            style={{
              textAlign: "left",
              padding: 10,
              background: active ? "var(--bg-3)" : "var(--bg-1)",
              border: `1px solid ${
                active ? priorityColor(c.triage_priority) : "var(--border-1)"
              }`,
              borderLeft: `4px solid ${priorityColor(c.triage_priority)}`,
              borderRadius: "var(--r2)",
              cursor: "pointer",
              color: "var(--text-0)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
              }}
            >
              <span style={{ fontWeight: 600 }}>{c.id}</span>
              <span
                style={{
                  color: priorityColor(c.triage_priority),
                  fontSize: 10,
                  letterSpacing: 1,
                  textTransform: "uppercase",
                  fontWeight: 600,
                }}
              >
                {c.triage_priority}
              </span>
            </div>
            <div
              style={{
                fontSize: 11,
                color: "var(--text-2)",
                marginTop: 4,
                display: "flex",
                justifyContent: "space-between",
              }}
            >
              <span>confidence</span>
              <span style={{ fontFamily: "var(--font-mono)" }}>
                {formatConfidence(c.confidence)}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
