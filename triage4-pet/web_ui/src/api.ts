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

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  submissions: () => get<SubmissionSummary[]>("/submissions"),
  submission: (id: string) => get<SubmissionDetail>(`/submissions/${id}`),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
};
