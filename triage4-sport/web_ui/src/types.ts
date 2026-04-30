export type RiskBand = "steady" | "monitor" | "hold";

export interface Health { service: string; version: string; session_count: number; }

export interface Assessment {
  athlete_token: string;
  form_asymmetry_safety: number;
  workload_load_safety: number;
  recovery_hr_safety: number;
  baseline_deviation_safety: number;
  overall: number;
  risk_band: RiskBand;
}

export interface SessionSummary {
  athlete_token: string;
  assessment: Assessment;
  coach_message_count: number;
  trainer_note_count: number;
  has_physician_alert: boolean;
}

export interface CoachMessage { athlete_token: string; text: string; }
export interface TrainerNote { athlete_token: string; text: string; }
export interface PhysicianAlert {
  athlete_token: string; text: string; reasoning_trace?: string;
}

export interface SessionDetail {
  athlete_token: string;
  sport: string | null;
  session_duration_s: number | null;
  assessment: Assessment;
  coach_messages: CoachMessage[];
  trainer_notes: TrainerNote[];
  physician_alert: PhysicianAlert | null;
}

export interface Report {
  session_count: number;
  band_counts: { steady: number; monitor: number; hold: number };
  sessions: SessionSummary[];
}
