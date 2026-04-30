export type AlertLevel = "ok" | "watch" | "urgent";

export interface Health {
  service: string; version: string;
  station_id: string; observation_count: number; alert_count: number;
}

export interface Score {
  obs_token: string;
  call_presence_safety: number;
  distress_safety: number;
  vitals_safety: number;
  thermal_safety: number;
  mortality_cluster_safety: number;
  overall: number;
  alert_level: AlertLevel;
}

export interface Alert {
  obs_token: string;
  kind: string;
  level: AlertLevel;
  text: string;
  location_handle: string;
  observed_value: number | null;
}

export interface Report {
  station_id: string;
  observation_count: number;
  level_counts: { ok: number; watch: number; urgent: number };
  scores: Score[];
  alerts: Alert[];
}
