export type AlertLevel = "ok" | "watch" | "urgent";

export interface Health {
  service: string; version: string;
  pool_id: string; swimmer_count: number; alert_count: number;
}

export interface Score {
  swimmer_token: string;
  submersion_safety: number;
  idr_safety: number;
  absent_safety: number;
  distress_safety: number;
  overall: number;
  alert_level: AlertLevel;
}

export interface Alert {
  swimmer_token: string;
  kind: string;
  level: AlertLevel;
  text: string;
  observed_value: number | null;
}

export interface Report {
  pool_id: string;
  swimmer_count: number;
  level_counts: { ok: number; watch: number; urgent: number };
  scores: Score[];
  alerts: Alert[];
}
