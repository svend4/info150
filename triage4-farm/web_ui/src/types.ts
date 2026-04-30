export type WelfareFlag = "well" | "concern" | "urgent";

export interface Health {
  service: string; version: string;
  farm_id: string; animal_count: number; alert_count: number;
}

export interface Score {
  animal_id: string;
  gait: number;
  respiratory: number;
  thermal: number;
  overall: number;
  flag: WelfareFlag;
}

export interface Alert {
  animal_id: string;
  kind: string;
  flag: WelfareFlag;
  text: string;
  observed_value: number | null;
}

export interface Report {
  farm_id: string;
  animal_count: number;
  herd_overall: number;
  flag_counts: { well: number; concern: number; urgent: number };
  scores: Score[];
  alerts: Alert[];
}
