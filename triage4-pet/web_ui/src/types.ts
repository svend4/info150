export type Recommendation = "can_wait" | "routine_visit" | "see_today";

export interface Health { service: string; version: string; submission_count: number; }

export interface Assessment {
  pet_token: string;
  gait_safety: number;
  respiratory_safety: number;
  cardiac_safety: number;
  pain_safety: number;
  overall: number;
  recommendation: Recommendation;
}

export interface SubmissionSummary { pet_token: string; assessment: Assessment; }

export interface OwnerMessage { pet_token: string; text: string; }

export interface SubmissionDetail {
  pet_token: string;
  species: string | null;
  age_years: number | null;
  assessment: Assessment;
  vet_summary: string;
  owner_messages: OwnerMessage[];
}

export interface Report {
  submission_count: number;
  recommendation_counts: { can_wait: number; routine_visit: number; see_today: number };
  submissions: SubmissionSummary[];
}
