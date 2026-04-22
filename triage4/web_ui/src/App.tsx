import { useState } from "react";

import AppLayout from "./components/layout/AppLayout";
import type { TabKey } from "./components/layout/TopBar";
import CasualtiesPage from "./pages/CasualtiesPage";
import GraphPage from "./pages/GraphPage";
import MapPage from "./pages/MapPage";
import MetricsPage from "./pages/MetricsPage";
import ReplayPage from "./pages/ReplayPage";
import TasksPage from "./pages/TasksPage";

export default function App() {
  const [tab, setTab] = useState<TabKey>("casualties");

  return (
    <AppLayout tab={tab} onTabChange={setTab}>
      {tab === "casualties" && <CasualtiesPage />}
      {tab === "tasks" && <TasksPage />}
      {tab === "map" && <MapPage />}
      {tab === "replay" && <ReplayPage />}
      {tab === "graph" && <GraphPage />}
      {tab === "metrics" && <MetricsPage />}
    </AppLayout>
  );
}
