import type { Cue, FormScore, Health, Report } from "./types";

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
  const r = await fetch(p, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${p} → ${r.status}`);
  return r.json() as Promise<T>;
}

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  reps: () => get<FormScore[]>("/reps"),
  rep: (idx: number) => get<FormScore & { cues: Cue[] }>(`/reps/${idx}`),
  cues: () => get<Cue[]>("/cues"),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
  cameraRun: (asymmetry_severity: number, rep_count: number, exercise: string) =>
    postJson<{ asymmetry_severity: number; rep_count: number; cue_count: number }>(
      "/camera/run",
      { asymmetry_severity, rep_count, exercise },
    ),
};
