import type { Alert, Health, Report, Score } from "./types";

async function get<T>(p: string): Promise<T> {
  const r = await fetch(p);
  if (!r.ok) throw new Error(`${p} → ${r.status}`);
  return r.json() as Promise<T>;
}
async function post<T>(p: string): Promise<T> {
  const r = await fetch(p, { method: "POST" });
  if (!r.ok) throw new Error(`${p} → ${r.status}`);
  return r.json() as Promise<T>;
}

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  windows: () => get<Score[]>("/windows"),
  window: (idx: number) => get<Score & { alerts: Alert[] }>(`/windows/${idx}`),
  alerts: () => get<Alert[]>("/alerts"),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
};
