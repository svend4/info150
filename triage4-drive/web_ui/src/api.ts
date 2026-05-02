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

export type DriveCameraBody = {
  session_id: string; drowsiness: number;
  distraction: number; incapacitation: number;
};

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  windows: () => get<Score[]>("/windows"),
  window: (idx: number) => get<Score & { alerts: Alert[] }>(`/windows/${idx}`),
  alerts: () => get<Alert[]>("/alerts"),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
  cameraRun: (body: DriveCameraBody) =>
    postJson<{ score_count?: number; alert_count?: number; submission_count?: number; tag_count?: number }>("/camera/run", body),
};
