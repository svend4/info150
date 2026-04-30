import type { FarmAlert, FarmReport, Health, PenScore } from "./types";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(path, { method: "POST" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<FarmReport>("/report"),
  pens: () => get<PenScore[]>("/pens"),
  pen: (id: string) =>
    get<PenScore & { alerts: FarmAlert[] }>(`/pens/${id}`),
  alerts: () => get<FarmAlert[]>("/alerts"),
  reload: () =>
    post<{ reloaded: boolean; pen_count: number; alert_count: number }>(
      "/demo/reload",
    ),
};
