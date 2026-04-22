import type { Priority } from "../../types";
import type { CasualtyFilters as Filters, SortDirection, SortKey } from "../../util/filters";

const ALL_PRIORITIES: (Priority | string)[] = [
  "immediate",
  "delayed",
  "minimal",
  "unknown",
];

type Props = {
  filters: Filters;
  onFiltersChange: (next: Filters) => void;
  sort: SortKey;
  direction: SortDirection;
  onSortChange: (key: SortKey, direction: SortDirection) => void;
  total: number;
  shown: number;
};

export default function CasualtyFilters({
  filters,
  onFiltersChange,
  sort,
  direction,
  onSortChange,
  total,
  shown,
}: Props) {
  const togglePriority = (p: string) => {
    const next = new Set(filters.priorities);
    if (next.has(p)) next.delete(p);
    else next.add(p);
    onFiltersChange({ ...filters, priorities: next });
  };

  return (
    <div
      style={{
        padding: 12,
        background: "var(--bg-1)",
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r2)",
        marginBottom: 12,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 10,
        }}
      >
        <input
          type="search"
          placeholder="search id…"
          value={filters.search}
          onChange={(e) =>
            onFiltersChange({ ...filters, search: e.target.value })
          }
          style={{ flex: 1 }}
        />
        <span
          style={{
            fontSize: 11,
            color: "var(--text-2)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {shown}/{total}
        </span>
      </div>

      <div
        style={{
          display: "flex",
          gap: 4,
          flexWrap: "wrap",
          marginBottom: 10,
        }}
      >
        {ALL_PRIORITIES.map((p) => (
          <button
            key={p}
            aria-pressed={filters.priorities.has(p)}
            onClick={() => togglePriority(p)}
            style={{ fontSize: 11, padding: "4px 8px" }}
          >
            {p}
          </button>
        ))}
      </div>

      <div
        style={{
          display: "flex",
          gap: 6,
          alignItems: "center",
          fontSize: 12,
        }}
      >
        <span style={{ color: "var(--text-2)" }}>sort</span>
        <select
          value={sort}
          onChange={(e) => onSortChange(e.target.value as SortKey, direction)}
          style={{ fontSize: 12, padding: "4px 6px" }}
        >
          <option value="priority">priority</option>
          <option value="confidence">confidence</option>
          <option value="id">id</option>
          <option value="last_seen">last seen</option>
        </select>
        <button
          onClick={() =>
            onSortChange(sort, direction === "asc" ? "desc" : "asc")
          }
          style={{ fontSize: 12, padding: "4px 8px" }}
          title={`direction: ${direction}`}
        >
          {direction === "asc" ? "↑" : "↓"}
        </button>
      </div>

      <div
        style={{
          marginTop: 10,
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontSize: 12,
        }}
      >
        <span style={{ color: "var(--text-2)" }}>min conf</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={filters.minConfidence}
          onChange={(e) =>
            onFiltersChange({
              ...filters,
              minConfidence: Number(e.target.value),
            })
          }
        />
        <span style={{ fontFamily: "var(--font-mono)", minWidth: 28 }}>
          {Math.round(filters.minConfidence * 100)}%
        </span>
      </div>
    </div>
  );
}
