// Hook that polls an async fetcher at a fixed interval.
//
// Generic over result type. Exposes {data, error, loading,
// lastFetch, refresh} so components don't reinvent the state
// machine every time. Pauses automatically when the tab is
// hidden (document.visibilityState) so we don't hammer the
// backend from a backgrounded window.

import { useCallback, useEffect, useRef, useState } from "react";

import { BackendError } from "../api/client";
import type { ApiError } from "../types";

export type PollingState<T> = {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  lastFetch: number | null;
  refresh: () => Promise<void>;
};

export function usePolling<T>(
  fetcher: (signal?: AbortSignal) => Promise<T>,
  intervalMs: number,
): PollingState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [lastFetch, setLastFetch] = useState<number | null>(null);
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
        setLastFetch(Date.now());
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
    let timer: number | undefined;

    const schedule = () => {
      if (typeof document !== "undefined" && document.hidden) return;
      timer = window.setTimeout(async () => {
        await refresh();
        schedule();
      }, intervalMs);
    };
    schedule();

    const handleVisibility = () => {
      if (typeof document !== "undefined" && !document.hidden) {
        refresh();
        schedule();
      } else if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      if (timer !== undefined) window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", handleVisibility);
      abortRef.current?.abort();
    };
  }, [intervalMs, refresh]);

  return { data, error, loading, lastFetch, refresh };
}
