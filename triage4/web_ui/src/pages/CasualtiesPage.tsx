// Casualties tab: filter / sort sidebar + selected detail pane.
// Adds compare mode (side-by-side two casualties) + export buttons.
// Polls /casualties every 10 s.

import { useEffect, useMemo, useState } from "react";

import { fetchCasualties } from "../api/endpoints";
import CasualtyDetail from "../components/casualties/CasualtyDetail";
import CasualtyFilters from "../components/casualties/CasualtyFilters";
import CasualtyList from "../components/casualties/CasualtyList";
import { usePolling } from "../hooks/usePolling";
import type { Casualty } from "../types";
import { downloadCsv, downloadJson } from "../util/export";
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
  const [compareMode, setCompareMode] = useState(false);
  const [compareId, setCompareId] = useState<string | null>(null);

  const all: Casualty[] = data ?? [];
  const shown = useMemo(() => {
    const filtered = filterCasualties(all, filters);
    return sortCasualties(filtered, sort, direction);
  }, [all, filters, sort, direction]);

  useEffect(() => {
    if (selectedId === null && shown.length > 0) {
      setSelectedId(shown[0].id);
    }
    if (selectedId !== null && !shown.some((c) => c.id === selectedId)) {
      setSelectedId(shown[0]?.id ?? null);
    }
  }, [shown, selectedId]);

  const selected = selectedId
    ? all.find((c) => c.id === selectedId) ?? null
    : null;
  const compared = compareId
    ? all.find((c) => c.id === compareId) ?? null
    : null;

  const onSelect = (c: Casualty) => {
    if (compareMode && selectedId !== null && selectedId !== c.id) {
      // second click in compare mode → set as compared casualty.
      setCompareId(c.id);
    } else {
      setSelectedId(c.id);
      setCompareId(null);
    }
  };

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
        <div
          style={{
            display: "flex",
            gap: 6,
            marginBottom: 10,
            flexWrap: "wrap",
          }}
        >
          <button
            aria-pressed={compareMode}
            onClick={() => {
              setCompareMode((v) => !v);
              setCompareId(null);
            }}
            style={{ fontSize: 11, padding: "4px 8px" }}
          >
            {compareMode ? "✓ compare" : "compare"}
          </button>
          <button
            onClick={() =>
              downloadCsv(
                shown.map((c) => ({
                  id: c.id,
                  priority: c.triage_priority,
                  confidence: c.confidence,
                  x: c.location.x,
                  y: c.location.y,
                  status: c.status,
                  platform_source: c.platform_source,
                })),
                "triage4_casualties.csv",
              )
            }
            disabled={shown.length === 0}
            style={{ fontSize: 11, padding: "4px 8px" }}
          >
            ↓ CSV
          </button>
          <button
            onClick={() =>
              downloadJson(shown, "triage4_casualties.json")
            }
            disabled={shown.length === 0}
            style={{ fontSize: 11, padding: "4px 8px" }}
          >
            ↓ JSON
          </button>
        </div>
        {compareMode && (
          <div
            style={{
              padding: 8,
              marginBottom: 10,
              background: "var(--bg-2)",
              border: "1px solid var(--accent-dim)",
              borderRadius: "var(--r1)",
              fontSize: 11,
              color: "var(--text-1)",
            }}
          >
            compare mode: click two casualties to view side-by-side
            {selectedId && (
              <div
                style={{ marginTop: 4, fontFamily: "var(--font-mono)" }}
              >
                A: <span style={{ color: "var(--accent)" }}>{selectedId}</span>
                {compareId && (
                  <>
                    {" · "}B:{" "}
                    <span style={{ color: "var(--accent)" }}>{compareId}</span>
                  </>
                )}
              </div>
            )}
          </div>
        )}
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
          onSelect={onSelect}
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
      <section
        style={
          compareMode && compared
            ? {
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 16,
                alignItems: "start",
              }
            : undefined
        }
      >
        <CasualtyDetail casualty={selected} />
        {compareMode && compared && <CasualtyDetail casualty={compared} />}
      </section>
    </div>
  );
}
