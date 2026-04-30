export type AlertLevel = "ok" | "watch" | "urgent";

export interface Health {
  service: string; version: string;
  site_id: string; worker_count: number; alert_count: number;
}

export interface Score {
  worker_token: string;
  ppe_compliance: number;
  lifting_safety: number;
  heat_safety: number;
  fatigue_safety: number;
  overall: number;
  alert_level: AlertLevel;
}

export interface Alert {
  worker_token: string;
  kind: string;
  level: AlertLevel;
  text: string;
  observed_value: number | null;
}

export interface Report {
  site_id: string;
  worker_count: number;
  level_counts: { ok: number; watch: number; urgent: number };
  scores: Score[];
  alerts: Alert[];
}
