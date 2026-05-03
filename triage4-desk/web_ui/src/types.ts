export type CueSeverity = "ok" | "minor" | "severe";
export type CueKind =
  | "fatigue" | "hydration" | "eye_strain" | "posture"
  | "microbreak" | "stretch" | "drowsiness" | "distraction";
export type WorkMode = "office" | "coding" | "meeting" | "gaming" | "streaming";
export type PostureAdvisory = "ok" | "slumped" | "leaning";

export interface Health {
  service: string; version: string;
  worker_id: string; work_mode: WorkMode; cue_count: number;
}

export interface Cue {
  kind: CueKind;
  severity: CueSeverity;
  text: string;
  observed_value: number | null;
}

export interface Report {
  worker_id: string;
  work_mode: WorkMode;
  session_min: number;
  minutes_since_break: number;
  minutes_since_stretch: number;
  fatigue_index: number;
  hydration_due: boolean;
  eye_break_due: boolean;
  microbreak_due: boolean;
  stretch_due: boolean;
  posture_advisory: PostureAdvisory;
  drowsiness_alert: boolean;
  distraction_alert: boolean;
  overall_safety: number;
  severity_counts: { ok: number; minor: number; severe: number };
  cues: Cue[];
}
