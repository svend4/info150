export type CueSeverity = "ok" | "minor" | "severe";
export type CueKind = "asymmetry" | "depth" | "tempo" | "breathing";

export interface Health {
  service: string; version: string;
  exercise: string; rep_count: number; cue_count: number;
}

export interface FormScore {
  rep_index: number;
  symmetry: number;
  depth: number;
  tempo: number;
  overall: number;
}

export interface Cue {
  rep_index: number | null;
  kind: CueKind;
  severity: CueSeverity;
  text: string;
  observed_value: number | null;
}

export interface Report {
  exercise: string;
  rep_count: number;
  session_overall: number;
  recovery_quality: number | null;
  severity_counts: { ok: number; minor: number; severe: number };
  form_scores: FormScore[];
  cues: Cue[];
}
