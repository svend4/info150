export type AlertLevel = "ok" | "check_in" | "urgent";

export interface Health {
  service: string; version: string;
  residence_id: string; window_count: number; alert_count: number;
}

export interface Score {
  window_id: string;
  fall_risk: number;
  activity_alignment: number;
  mobility_trend: number;
  overall: number;
  alert_level: AlertLevel;
}

export interface Alert {
  window_id: string;
  kind: string;
  level: AlertLevel;
  text: string;
  observed_value: number | null;
}

export interface Report {
  residence_id: string;
  window_count: number;
  level_counts: { ok: number; check_in: number; urgent: number };
  scores: Score[];
  alerts: Alert[];
}
