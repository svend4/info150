export type AlertLevel = "ok" | "watch" | "urgent";

export interface Health {
  service: string; version: string;
  venue_id: string; zone_count: number; alert_count: number;
}

export interface Score {
  zone_id: string;
  density_safety: number;
  flow_safety: number;
  pressure_safety: number;
  medical_safety: number;
  overall: number;
  alert_level: AlertLevel;
}

export interface Alert {
  zone_id: string;
  kind: string;
  level: AlertLevel;
  text: string;
  observed_value: number | null;
}

export interface Report {
  venue_id: string;
  zone_count: number;
  level_counts: { ok: number; watch: number; urgent: number };
  scores: Score[];
  alerts: Alert[];
}
