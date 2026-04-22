import { useState } from "react";

import AppLayout from "./components/layout/AppLayout";
import type { TabKey } from "./components/layout/TopBar";
import CasualtiesPage from "./pages/CasualtiesPage";
import ForecastPage from "./pages/ForecastPage";
import GraphPage from "./pages/GraphPage";
import MapPage from "./pages/MapPage";
import MetricsPage from "./pages/MetricsPage";
import MissionPage from "./pages/MissionPage";
import ReplayPage from "./pages/ReplayPage";
import ScorecardPage from "./pages/ScorecardPage";
import TasksPage from "./pages/TasksPage";

export default function App() {
  const [tab, setTab] = useState<TabKey>("casualties");

  return (
    <AppLayout tab={tab} onTabChange={setTab}>
      {tab === "casualties" && <CasualtiesPage />}
      {tab === "mission" && <MissionPage />}
      {tab === "forecast" && <ForecastPage />}
      {tab === "scorecard" && <ScorecardPage />}
      {tab === "tasks" && <TasksPage />}
      {tab === "map" && <MapPage />}
      {tab === "replay" && <ReplayPage />}
      {tab === "graph" && <GraphPage />}
      {tab === "metrics" && <MetricsPage />}
    </AppLayout>
  );
}
