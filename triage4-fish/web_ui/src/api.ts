import type { FarmAlert, FarmReport, Health, PenScore } from "./types";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(path, { method: "POST" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}
async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export type FishCameraBody = {
  pen_id: string; species: string;
  school_disruption: number; turbidity_safety: number;
  gill_anomaly: number; sea_lice_burden: number;
  mortality_count: number; do_drop: number; temp_anomaly: number;
};

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<FarmReport>("/report"),
  pens: () => get<PenScore[]>("/pens"),
  pen: (id: string) =>
    get<PenScore & { alerts: FarmAlert[] }>(`/pens/${id}`),
  alerts: () => get<FarmAlert[]>("/alerts"),
  reload: () =>
    post<{ reloaded: boolean; pen_count: number; alert_count: number }>(
      "/demo/reload",
    ),
  cameraRun: (body: FishCameraBody) =>
    postJson<{ score_count: number; alert_count: number }>("/camera/run", body),
};
