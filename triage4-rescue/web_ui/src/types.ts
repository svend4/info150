export type StartTag = "immediate" | "delayed" | "minor" | "deceased";
export type AgeGroup = "adult" | "pediatric";
export type CueSeverity = "info" | "advisory" | "flag";

export interface Health {
  service: string;
  version: string;
  incident_id: string;
  casualty_count: number;
}

export interface Casualty {
  casualty_id: string;
  tag: StartTag;
  age_group: AgeGroup;
  age_years: number | null;
  reasoning: string;
  flag_for_secondary_review: boolean;
}

export interface Cue {
  casualty_id: string;
  kind: string;
  severity: CueSeverity;
  text: string;
  observed_value: number | null;
}

export interface Counts {
  immediate: number;
  delayed: number;
  minor: number;
  deceased: number;
}

export interface Incident {
  incident_id: string;
  casualty_count: number;
  counts: Counts;
  assessments: Casualty[];
  cues: Cue[];
}
