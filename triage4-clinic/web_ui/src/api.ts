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
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${p} → ${r.status}`);
  return r.json() as Promise<T>;
}

export type ClinicCameraBody = {
  patient_token: string;
  postural_instability: number;
  hr_elevation: number; rr_elevation: number;
  cough_frequency: number; acoustic_strain: number;
};

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  submissions: () => get<SubmissionSummary[]>("/submissions"),
  submission: (id: string) => get<SubmissionDetail>(`/submissions/${id}`),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
  cameraRun: (body: ClinicCameraBody) =>
    postJson<{ score_count?: number; alert_count?: number; submission_count?: number; tag_count?: number }>("/camera/run", body),
};
