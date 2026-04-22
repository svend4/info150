// Casualties tab: filter / sort sidebar + selected detail pane.
// Lives-view polls /casualties every 10 s so edits on the backend
// (via a seed refresh or an external graph update) appear without
// a manual refresh.

import { useEffect, useMemo, useState } from "react";

import { fetchCasualties } from "../api/endpoints";
import CasualtyDetail from "../components/casualties/CasualtyDetail";
import CasualtyFilters from "../components/casualties/CasualtyFilters";
import CasualtyList from "../components/casualties/CasualtyList";
import { usePolling } from "../hooks/usePolling";
import type { Casualty } from "../types";
import {
  defaultFilters,
  filterCasualties,
  sortCasualties,
  type CasualtyFilters as Filters,
  type SortDirection,
  type SortKey,
} from "../util/filters";

export default function CasualtiesPage() {
  const { data, error, loading, lastFetch, refresh } = usePolling(
    fetchCasualties,
    10_000,
  );
  const [filters, setFilters] = useState<Filters>(defaultFilters());
  const [sort, setSort] = useState<SortKey>("priority");
  const [direction, setDirection] = useState<SortDirection>("asc");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const all: Casualty[] = data ?? [];
  const shown = useMemo(() => {
    const filtered = filterCasualties(all, filters);
    return sortCasualties(filtered, sort, direction);
  }, [all, filters, sort, direction]);

  // Auto-select the first item once data lands.
  useEffect(() => {
    if (selectedId === null && shown.length > 0) {
      setSelectedId(shown[0].id);
    }
    // If the selected id disappears after a filter change, clear selection.
    if (selectedId !== null && !shown.some((c) => c.id === selectedId)) {
      setSelectedId(shown[0]?.id ?? null);
    }
  }, [shown, selectedId]);

  const selected = selectedId
    ? all.find((c) => c.id === selectedId) ?? null
    : null;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "340px 1fr",
        gap: 16,
        alignItems: "start",
      }}
    >
      <aside>
        <CasualtyFilters
          filters={filters}
          onFiltersChange={setFilters}
          sort={sort}
          direction={direction}
          onSortChange={(k, d) => {
            setSort(k);
            setDirection(d);
          }}
          total={all.length}
          shown={shown.length}
        />
        {loading && all.length === 0 && (
          <div
            style={{
              padding: 16,
              color: "var(--text-2)",
              fontStyle: "italic",
            }}
          >
            loading casualties…
          </div>
        )}
        {error && (
          <div
            style={{
              padding: 12,
              background: "var(--bg-1)",
              border: "1px solid var(--err)",
              borderRadius: "var(--r2)",
              color: "var(--err)",
              fontSize: 12,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              failed to load
            </div>
            <div>{error.message}</div>
            <button
              onClick={refresh}
              style={{ marginTop: 8, fontSize: 11, padding: "4px 8px" }}
            >
              retry
            </button>
          </div>
        )}
        <CasualtyList
          items={shown}
          selectedId={selectedId}
          onSelect={(c) => setSelectedId(c.id)}
        />
        <div
          style={{
            marginTop: 10,
            fontSize: 10,
            color: "var(--text-2)",
            fontFamily: "var(--font-mono)",
            textAlign: "right",
          }}
        >
          last fetch: {lastFetch ? new Date(lastFetch).toLocaleTimeString() : "—"}
        </div>
      </aside>
      <section>
        <CasualtyDetail casualty={selected} />
      </section>
    </div>
  );
}
