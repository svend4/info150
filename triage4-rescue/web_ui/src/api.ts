import type { Casualty, Cue, Health, Incident } from "./types";

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
  incident: () => get<Incident>("/incident"),
  casualties: () => get<Casualty[]>("/casualties"),
  casualty: (id: string) => get<Casualty & { cues: Cue[] }>(`/casualties/${id}`),
  alerts: () => get<Cue[]>("/alerts"),
  reload: () => post<{ reloaded: boolean; incident_id: string; casualty_count: number }>(
    "/demo/reload",
  ),
};
