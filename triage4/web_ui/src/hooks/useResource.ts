// One-shot resource loader (the fetch-once case). Complements
// usePolling: no interval, just load on mount + when deps change,
// with the same {data, error, loading, refresh} surface.

import { useCallback, useEffect, useRef, useState } from "react";

import { BackendError } from "../api/client";
import type { ApiError } from "../types";

export type ResourceState<T> = {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  refresh: () => Promise<void>;
};

export function useResource<T>(
  fetcher: (signal?: AbortSignal) => Promise<T>,
  deps: readonly unknown[] = [],
): ResourceState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const abortRef = useRef<AbortController | null>(null);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    try {
      const value = await fetcherRef.current(controller.signal);
      if (!controller.signal.aborted) {
        setData(value);
        setError(null);
      }
    } catch (exc) {
      if (controller.signal.aborted) return;
      if (exc instanceof BackendError) setError(exc.toApiError());
      else if (exc instanceof Error)
        setError({ status: 0, message: exc.message, url: "" });
      else setError({ status: 0, message: String(exc), url: "" });
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    return () => {
      abortRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, loading, refresh };
}
