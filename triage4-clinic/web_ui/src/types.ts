export type Recommendation = "self_care" | "schedule" | "urgent_review";

export interface Health { service: string; version: string; submission_count: number; alert_count: number; }

export interface Assessment {
  patient_token: string;
  cardiac_safety: number;
  respiratory_safety: number;
  acoustic_safety: number;
  postural_safety: number;
  overall: number;
  recommendation: Recommendation;
}

export interface SubmissionSummary {
  patient_token: string;
  assessment: Assessment;
  alert_count: number;
  symptom_count: number;
}

export interface Alert {
  patient_token: string;
  channel: string;
  recommendation: Recommendation;
  text: string;
  reasoning_trace?: string;
  alternative_explanations?: string[];
}

export interface SubmissionDetail {
  patient_token: string;
  assessment: Assessment;
  alerts: Alert[];
  readings: Record<string, unknown>[];
  reported_symptoms: string[];
}

export interface Report {
  submission_count: number;
  recommendation_counts: { self_care: number; schedule: number; urgent_review: number };
  submissions: SubmissionSummary[];
}
