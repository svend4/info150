// Minimal query-string router. Reads and writes ?tab=...&id=...
// from location.search. No react-router dep; history.replaceState
// keeps the back-button free of polluted entries.

import { useCallback, useEffect, useState } from "react";

export type QueryState = Record<string, string>;

function readQuery(): QueryState {
  const out: QueryState = {};
  const params = new URLSearchParams(window.location.search);
  params.forEach((value, key) => {
    out[key] = value;
  });
  return out;
}

function writeQuery(state: QueryState): void {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(state)) {
    if (v != null && v !== "") params.set(k, v);
  }
  const qs = params.toString();
  const path =
    window.location.pathname +
    (qs ? `?${qs}` : "") +
    window.location.hash;
  window.history.replaceState(null, "", path);
}

export function useQuerySync() {
  const [state, setState] = useState<QueryState>(() => readQuery());

  // Apply external navigation (back/forward).
  useEffect(() => {
    const handler = () => setState(readQuery());
    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  }, []);

  const update = useCallback((patch: QueryState) => {
    setState((current) => {
      const next = { ...current, ...patch };
      for (const [k, v] of Object.entries(patch)) {
        if (v == null || v === "") delete next[k];
      }
      writeQuery(next);
      return next;
    });
  }, []);

  return { state, update };
}
