export type CueSeverity = "ok" | "minor" | "severe";
export type CueKind = "fatigue" | "hydration" | "shade" | "pace" | "rest";
export type Terrain = "flat" | "hilly" | "stairs" | "mixed";
export type PaceAdvisory = "slow_down" | "continue" | "speed_up";

export interface Health {
  service: string; version: string;
  walker_id: string; terrain: Terrain; cue_count: number;
}

export interface Cue {
  kind: CueKind;
  severity: CueSeverity;
  text: string;
  observed_value: number | null;
}

export interface Report {
  walker_id: string;
  terrain: Terrain;
  duration_min: number;
  pace_kmh: number;
  fatigue_index: number;
  hydration_due: boolean;
  shade_advisory: boolean;
  pace_advisory: PaceAdvisory;
  rest_due: boolean;
  overall_safety: number;
  severity_counts: { ok: number; minor: number; severe: number };
  cues: Cue[];
}
