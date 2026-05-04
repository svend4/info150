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

export type DeskCameraBody = {
  worker_id: string;
  work_mode: string;
  session_min: number;
  minutes_since_break: number;
  minutes_since_stretch: number;
  typing_intensity: number;
  screen_motion_proxy: number;
  ambient_light_proxy: number;
  posture_quality: number;
  drowsiness_signal: number;
  distraction_signal: number;
  air_temp_c: number | null;
  hr_bpm: number | null;
};

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  cues: () => get<Cue[]>("/cues"),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
  cameraRun: (body: DeskCameraBody) =>
    postJson<{
      fatigue_index: number;
      posture_advisory: string;
      overall_safety: number;
      cue_count: number;
    }>("/camera/run", body),
};
