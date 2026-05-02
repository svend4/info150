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
  const r = await fetch(p, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${p} → ${r.status}`);
  return r.json() as Promise<T>;
}

export type CoastCameraBody = {
  zone_id?: string;
  zone_kind?: string;
  density_pressure: number;
  in_water_motion: number;
  sun_intensity: number;
  lost_child_flag: boolean;
};

export type HistoryPoint = { ts: number; value: number };
export type HistoryResponse = {
  zone_id: string;
  channel: string;
  hours: number;
  points: HistoryPoint[];
};

export type CameraHealthRow = {
  source: string;
  state: "ok" | "stale" | "down" | "unknown";
  last_frame_ts_unix: number | null;
  frames_seen: number;
  frames_dropped: number;
  fps: number;
  last_error: string | null;
};

export type AggregateBucket = {
  ts_unix: number;
  ok: number;
  watch: number;
  urgent: number;
};
export type AggregatesResponse = {
  hours: number;
  bucket_minutes: number;
  buckets: AggregateBucket[];
};

export type HourlyBucket = { hour_ago: number; mean_value: number; n_samples: number };
export type HourlyResponse = {
  zone_id: string; channel: string; hours: number;
  buckets: HourlyBucket[];
};

export type BroadcastEntry = {
  ts_unix: number;
  kind: string;
  message: string;
  zone_id: string | null;
  operator_id: string | null;
};
export type BroadcastLogResponse = {
  kinds: string[];
  entries: BroadcastEntry[];
};
export type BroadcastSendBody = {
  kind: string;
  message: string;
  zone_id?: string | null;
  operator_id?: string | null;
};

export const api = {
  health: () => get<Health>("/health"),
  report: () => get<Report>("/report"),
  zones: () => get<Score[]>("/zones"),
  zone: (id: string) => get<Score & { alerts: Alert[] }>(`/zones/${id}`),
  alerts: () => get<Alert[]>("/alerts"),
  reload: () => post<{ reloaded: boolean }>("/demo/reload"),
  cameraRun: (body: CoastCameraBody) =>
    postJson<{ zone_count: number; alert_count: number }>("/camera/run", body),
  zoneHistory: (zoneId: string, channel: string, hours = 24) =>
    get<HistoryResponse>(
      `/zones/${encodeURIComponent(zoneId)}/history`
        + `?channel=${channel}&hours=${hours}`,
    ),
  camerasHealth: () => get<{ cameras: CameraHealthRow[] }>("/cameras/health"),
  cameraReport: (source: string, ok: boolean, error?: string) =>
    postJson<{ acknowledged: boolean }>(
      "/cameras/report", { source, ok, error: error ?? null },
    ),
  coastAggregates: (hours = 4, bucketMinutes = 5) =>
    get<AggregatesResponse>(
      `/coast/aggregates?hours=${hours}&bucket_minutes=${bucketMinutes}`,
    ),
  zoneHourly: (zoneId: string, channel = "overall", hours = 24) =>
    get<HourlyResponse>(
      `/zones/${encodeURIComponent(zoneId)}/hourly`
        + `?channel=${channel}&hours=${hours}`,
    ),
  broadcastSend: (body: BroadcastSendBody) =>
    postJson<{ recorded: boolean; entry: BroadcastEntry }>(
      "/broadcast", body,
    ),
  broadcastLog: (limit = 50) =>
    get<BroadcastLogResponse>(`/broadcast/log?limit=${limit}`),
};
