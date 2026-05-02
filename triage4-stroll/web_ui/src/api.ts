import type { Cue, Health, Report } from "./types";

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

export type StrollCameraBody = {
  walker_id: string;
  terrain: string;
  pace_kmh: number;
  duration_min: number;
  activity_intensity: number;
  sun_exposure_proxy: number;
  minutes_since_rest: number;
  air_temp_c: number | null;
  hr_bpm: number | null;
};

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  cues: () => get<Cue[]>("/cues"),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
  cameraRun: (body: StrollCameraBody) =>
    postJson<{ fatigue_index: number; pace_advisory: string;
               overall_safety: number; cue_count: number }>(
      "/camera/run", body,
    ),
};
