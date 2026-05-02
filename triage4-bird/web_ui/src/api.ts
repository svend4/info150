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

export type BirdCameraBody = {
  obs_token: string; station_id: string; presence_rate: number;
  expected_species_present_fraction: number; distress_fraction: number;
  wingbeat_anomaly: number; thermal_elevation: number; dead_bird_count: number;
};

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  observations: () => get<Score[]>("/observations"),
  observation: (id: string) => get<Score & { alerts: Alert[] }>(`/observations/${id}`),
  alerts: () => get<Alert[]>("/alerts"),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
  cameraRun: (body: BirdCameraBody) =>
    postJson<{ score_count: number; alert_count: number }>("/camera/run", body),
};
