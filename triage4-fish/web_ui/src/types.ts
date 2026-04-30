export type WelfareLevel = "steady" | "watch" | "urgent";

export interface Health {
  service: string;
  version: string;
  farm_id: string;
  pen_count: number;
  alert_count: number;
}

export interface PenScore {
  pen_id: string;
  gill_rate_safety: number;
  school_cohesion_safety: number;
  sea_lice_safety: number;
  mortality_safety: number;
  water_chemistry_safety: number;
  overall: number;
  welfare_level: WelfareLevel;
  species?: string | null;
  location_handle?: string | null;
}

export interface FarmAlert {
  pen_id: string;
  kind: string;
  level: WelfareLevel;
  text: string;
  location_handle: string;
  observed_value: number | null;
}

export interface FarmReport {
  farm_id: string;
  pen_count: number;
  level_counts: { steady: number; watch: number; urgent: number };
  scores: PenScore[];
  alerts: FarmAlert[];
}
