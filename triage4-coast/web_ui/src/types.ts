export type AlertLevel = "ok" | "watch" | "urgent";
export type ZoneKind = "beach" | "promenade" | "water" | "pier";
export type AlertKind = "density" | "drowning" | "sun" | "lost_child"
  | "fall_event" | "stationary_person" | "flow_anomaly" | "slip_risk"
  | "calibration";

export interface Health {
  service: string; version: string;
  coast_id: string; zone_count: number; alert_count: number;
}

export interface Score {
  zone_id: string;
  zone_kind: ZoneKind;
  density_safety: number;
  drowning_safety: number;
  sun_safety: number;
  lost_child_safety: number;
  fall_event_safety: number;
  stationary_person_safety: number;
  flow_anomaly_safety: number;
  slip_risk_safety: number;
  overall: number;
  alert_level: AlertLevel;
}

export interface Alert {
  zone_id: string;
  kind: AlertKind;
  level: AlertLevel;
  text: string;
}

export interface Report {
  coast_id: string;
  zone_count: number;
  level_counts: { ok: number; watch: number; urgent: number };
  scores: Score[];
  alerts: Alert[];
}
