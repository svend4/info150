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
async function postJson<T>(p: string, body: unknown): Promise<T> {
  const r = await fetch(p, { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${p} → ${r.status}`);
  return r.json() as Promise<T>;
}

export type WildCameraBody = {
  obs_token?: string; species?: string; species_confidence?: number;
  presence_rate: number;
  limb_asymmetry: number; thermal_hotspot: number;
  postural_down_fraction: number; body_condition: number;
};

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  observations: () => get<Score[]>("/observations"),
  observation: (id: string) => get<Score & { alerts: Alert[] }>(`/observations/${id}`),
  alerts: () => get<Alert[]>("/alerts"),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
  cameraRun: (body: WildCameraBody) =>
    postJson<{ score_count: number; alert_count: number }>("/camera/run", body),
};
