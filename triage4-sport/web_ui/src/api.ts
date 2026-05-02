import type { Health, Report, SessionDetail, SessionSummary } from "./types";

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

export type SportCameraBody = {
  athlete_token: string; sport: string;
  workload_intensity: number; form_asymmetry: number;
  recovery_drop_bpm: number;
};

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  sessions: () => get<SessionSummary[]>("/sessions"),
  session: (id: string) => get<SessionDetail>(`/sessions/${id}`),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
  cameraRun: (body: SportCameraBody) =>
    postJson<{ score_count?: number; alert_count?: number; submission_count?: number; tag_count?: number }>("/camera/run", body),
};
