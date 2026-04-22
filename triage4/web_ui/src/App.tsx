import { useEffect, useState } from "react";

import AppLayout from "./components/layout/AppLayout";
import type { TabKey } from "./components/layout/TopBar";
import { useHotkeys } from "./hooks/useHotkeys";
import { useQuerySync } from "./hooks/useQuerySync";
import CasualtiesPage from "./pages/CasualtiesPage";
import ForecastPage from "./pages/ForecastPage";
import GraphPage from "./pages/GraphPage";
import HomePage from "./pages/HomePage";
import MapPage from "./pages/MapPage";
import MetricsPage from "./pages/MetricsPage";
import MissionPage from "./pages/MissionPage";
import ReplayPage from "./pages/ReplayPage";
import ScorecardPage from "./pages/ScorecardPage";
import SensingPage from "./pages/SensingPage";
import TasksPage from "./pages/TasksPage";
import { useToast } from "./state/ToastContext";

const TAB_KEYS: readonly TabKey[] = [
  "home",
  "casualties",
  "mission",
  "forecast",
  "scorecard",
  "tasks",
  "sensing",
  "map",
  "replay",
  "graph",
  "metrics",
];

// 1-9 cover 9 primary tabs; Map / Replay / Graph / Metrics share
// hotkeys 7-0 (since most workflows keep those as rare "navigate
// away from core triage" destinations). Sensing gets 7.
const HOTKEY_TAB_MAP: Record<string, TabKey> = {
  "1": "home",
  "2": "casualties",
  "3": "mission",
  "4": "forecast",
  "5": "scorecard",
  "6": "tasks",
  "7": "sensing",
  "8": "map",
  "9": "replay",
  "0": "metrics",
};

function parseTabFromQuery(q: string | undefined): TabKey {
  if (q && (TAB_KEYS as readonly string[]).includes(q)) {
    return q as TabKey;
  }
  return "home";
}

export default function App() {
  const { state, update } = useQuerySync();
  const [tab, setTab] = useState<TabKey>(() => parseTabFromQuery(state.tab));
  const [showHelp, setShowHelp] = useState(false);
  const toast = useToast();

  // state → query string.
  useEffect(() => {
    update({ tab });
  }, [tab, update]);

  // back/forward → state.
  useEffect(() => {
    const next = parseTabFromQuery(state.tab);
    if (next !== tab) setTab(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.tab]);

  useHotkeys({
    ...Object.fromEntries(
      Object.entries(HOTKEY_TAB_MAP).map(([k, v]) => [
        k,
        () => {
          setTab(v);
          toast.push(`→ ${v}`, "info", 1200);
        },
      ]),
    ),
    "?": () => setShowHelp((v) => !v),
    "shift+?": () => setShowHelp((v) => !v),
    escape: () => setShowHelp(false),
  });

  return (
    <AppLayout tab={tab} onTabChange={setTab}>
      {tab === "home" && <HomePage />}
      {tab === "casualties" && <CasualtiesPage />}
      {tab === "mission" && <MissionPage />}
      {tab === "forecast" && <ForecastPage />}
      {tab === "scorecard" && <ScorecardPage />}
      {tab === "tasks" && <TasksPage />}
      {tab === "sensing" && <SensingPage />}
      {tab === "map" && <MapPage />}
      {tab === "replay" && <ReplayPage />}
      {tab === "graph" && <GraphPage />}
      {tab === "metrics" && <MetricsPage />}

      {showHelp && <HelpOverlay onClose={() => setShowHelp(false)} />}
    </AppLayout>
  );
}

function HelpOverlay({ onClose }: { onClose: () => void }) {
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--bg-1)",
          border: "1px solid var(--border-2)",
          borderRadius: "var(--r3)",
          padding: 24,
          maxWidth: 460,
          width: "90%",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 14,
          }}
        >
          <h2 style={{ margin: 0, fontSize: 18 }}>Keyboard shortcuts</h2>
          <button onClick={onClose} style={{ fontSize: 11, padding: "4px 8px" }}>
            close (esc)
          </button>
        </div>
        <table
          style={{
            width: "100%",
            fontSize: 13,
            borderCollapse: "collapse",
          }}
        >
          <tbody>
            {[
              ["1", "Home"],
              ["2", "Casualties"],
              ["3", "Mission"],
              ["4", "Forecast"],
              ["5", "Scorecard"],
              ["6", "Tasks"],
              ["7", "Sensing"],
              ["8", "Map"],
              ["9", "Replay"],
              ["0", "Metrics"],
              ["?", "Show / hide this help"],
              ["Esc", "Close overlay"],
            ].map(([k, label]) => (
              <tr key={k}>
                <td
                  style={{
                    padding: "4px 8px 4px 0",
                    width: 60,
                    fontFamily: "var(--font-mono)",
                    color: "var(--accent)",
                  }}
                >
                  {k}
                </td>
                <td style={{ padding: "4px 0", color: "var(--text-1)" }}>
                  {label}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div
          style={{
            marginTop: 14,
            fontSize: 11,
            color: "var(--text-2)",
          }}
        >
          Shortcuts are disabled while typing in search / input fields.
        </div>
      </div>
    </div>
  );
}
