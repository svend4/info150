import type { Health, Report, SubmissionDetail, SubmissionSummary } from "./types";

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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${p} → ${r.status}`);
  return r.json() as Promise<T>;
}

export type PetCameraBody = {
  pet_token?: string; species?: string; age_years?: number;
  activity_proxy: number; gait_asymmetry: number;
  respiratory_elevation: number; cardiac_elevation: number;
  pain_behavior_count: number;
};

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  submissions: () => get<SubmissionSummary[]>("/submissions"),
  submission: (id: string) => get<SubmissionDetail>(`/submissions/${id}`),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
  cameraRun: (body: PetCameraBody) => postJson<{ recommendation: string }>("/camera/run", body),
};
