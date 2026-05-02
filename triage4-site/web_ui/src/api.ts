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

export type SiteCameraBody = {
  worker_token: string; fatigue: number;
  ppe_compliance: number; unsafe_lifting: number; heat_stress: number;
};

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  workers: () => get<Score[]>("/workers"),
  worker: (id: string) => get<Score & { alerts: Alert[] }>(`/workers/${id}`),
  alerts: () => get<Alert[]>("/alerts"),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
  cameraRun: (body: SiteCameraBody) =>
    postJson<{ score_count?: number; alert_count?: number; submission_count?: number; tag_count?: number }>("/camera/run", body),
};
