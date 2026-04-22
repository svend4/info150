// Sort / filter predicates for the casualty list. Pure functions,
// no React, trivially unit-testable.

import type { Casualty, Priority } from "../types";

export type SortKey = "priority" | "confidence" | "id" | "last_seen";
export type SortDirection = "asc" | "desc";

export type CasualtyFilters = {
  priorities: Set<Priority | string>;
  search: string;
  minConfidence: number;
};

const _PRIORITY_RANK: Record<string, number> = {
  immediate: 0,
  delayed: 1,
  minimal: 2,
  unknown: 3,
  expectant: 4,
};

export function defaultFilters(): CasualtyFilters {
  return {
    priorities: new Set<string>(["immediate", "delayed", "minimal", "unknown", "expectant"]),
    search: "",
    minConfidence: 0,
  };
}

export function filterCasualties(
  items: Casualty[],
  filters: CasualtyFilters,
): Casualty[] {
  const q = filters.search.trim().toLowerCase();
  return items.filter((c) => {
    if (!filters.priorities.has(c.triage_priority)) return false;
    if (c.confidence < filters.minConfidence) return false;
    if (q && !c.id.toLowerCase().includes(q)) return false;
    return true;
  });
}

export function sortCasualties(
  items: Casualty[],
  key: SortKey,
  direction: SortDirection,
): Casualty[] {
  const out = [...items];
  out.sort((a, b) => {
    let diff = 0;
    switch (key) {
      case "priority":
        diff =
          (_PRIORITY_RANK[a.triage_priority] ?? 99) -
          (_PRIORITY_RANK[b.triage_priority] ?? 99);
        break;
      case "confidence":
        diff = a.confidence - b.confidence;
        break;
      case "id":
        diff = a.id.localeCompare(b.id);
        break;
      case "last_seen":
        diff = (a.last_seen_ts ?? 0) - (b.last_seen_ts ?? 0);
        break;
    }
    return direction === "asc" ? diff : -diff;
  });
  return out;
}
