export type AlertLevel = "ok" | "caution" | "critical";

export interface Health {
  service: string; version: string;
  session_id: string; window_count: number; alert_count: number;
}

export interface Score {
  session_id: string;
  perclos: number;
  distraction: number;
  incapacitation: number;
  overall: number;
  alert_level: AlertLevel;
  index?: number;
}

export interface Alert {
  session_id: string;
  kind: string;
  level: AlertLevel;
  text: string;
  observed_value: number | null;
}

export interface Report {
  session_id: string;
  window_count: number;
  level_counts: { ok: number; caution: number; critical: number };
  scores: Score[];
  alerts: Alert[];
}
