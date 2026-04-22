import HealthBadge from "./HealthBadge";

export type TabKey =
  | "casualties"
  | "mission"
  | "forecast"
  | "scorecard"
  | "tasks"
  | "map"
  | "replay"
  | "graph"
  | "metrics";

const TABS: { key: TabKey; label: string }[] = [
  { key: "casualties", label: "Casualties" },
  { key: "mission", label: "Mission" },
  { key: "forecast", label: "Forecast" },
  { key: "scorecard", label: "Scorecard" },
  { key: "tasks", label: "Tasks" },
  { key: "map", label: "Map" },
  { key: "replay", label: "Replay" },
  { key: "graph", label: "Graph" },
  { key: "metrics", label: "Metrics" },
];

type Props = {
  active: TabKey;
  onChange: (tab: TabKey) => void;
};

export default function TopBar({ active, onChange }: Props) {
  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 20px",
        background: "var(--bg-1)",
        borderBottom: "1px solid var(--border-1)",
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <div
          style={{
            fontWeight: 700,
            fontSize: 16,
            letterSpacing: 0.5,
          }}
        >
          triage4
          <span
            style={{
              marginLeft: 8,
              fontSize: 11,
              opacity: 0.6,
              fontWeight: 400,
            }}
          >
            decision-support
          </span>
        </div>
        <nav style={{ display: "flex", gap: 4 }}>
          {TABS.map((tab) => (
            <button
              key={tab.key}
              aria-pressed={active === tab.key}
              onClick={() => onChange(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>
      <HealthBadge />
    </header>
  );
}
