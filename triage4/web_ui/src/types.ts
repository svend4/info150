// Full type surface for the triage4 dashboard.
//
// Shapes mirror FastAPI responses in triage4/ui/dashboard_api.py.
// When a backend schema changes, update here first — every
// consumer in web_ui/src/ imports from this file.

export type Priority = "immediate" | "delayed" | "minimal" | "unknown" | "expectant";

// --- casualties --------------------------------------------------------

export type GeoPose = { x: number; y: number; z: number };

export type TraumaHypothesis = {
  kind: string;
  score: number;
  explanation: string;
};

export type CasualtySignature = {
  bleeding_visual_score: number;
  perfusion_drop_score: number;
  chest_motion_fd: number;
  thermal_asymmetry_score?: number;
  posture_instability_score?: number;
  visibility_score?: number;
  breathing_curve?: number[];
  body_region_polygons?: Record<string, [number, number][]>;
  raw_features?: Record<string, number>;
};

export type Casualty = {
  id: string;
  triage_priority: Priority | string;
  confidence: number;
  platform_source: string;
  status: string;
  location: GeoPose;
  hypotheses: TraumaHypothesis[];
  signatures: CasualtySignature;
  first_seen_ts?: number;
  last_seen_ts?: number;
  assigned_medic?: string | null;
  assigned_robot?: string | null;
};

// --- explain + handoff --------------------------------------------------

export type Explanation = {
  casualty_id: string;
  priority: string;
  confidence: number;
  top_hypotheses: { kind: string; score: number; why: string }[];
};

export type HandoffPayload = {
  casualty_id: string;
  location: GeoPose;
  priority: string;
  confidence: number;
  top_hypotheses: { kind: string; score: number; explanation?: string }[];
  recommended_action: string;
};

// --- tasks --------------------------------------------------------------

export type TaskRecommendation = {
  casualty_id: string;
  priority: string;
  confidence: number;
  location: { x: number; y: number };
};

// --- map / replay -------------------------------------------------------

export type MapCasualty = {
  id: string;
  x: number;
  y: number;
  priority: string;
  confidence: number;
};

export type MapPlatform = {
  id: string;
  x: number;
  y: number;
  kind: string;
};

export type MapData = {
  platforms: MapPlatform[];
  casualties: MapCasualty[];
};

export type ReplayFrame = {
  t: number;
  platforms: MapPlatform[];
  casualties: MapCasualty[];
};

export type ReplayData = { frames: ReplayFrame[] };

// --- graph --------------------------------------------------------------

export type GraphNode = Casualty;

export type GraphEdge = [string, string, string]; // [src, relation, dst]

export type GraphData = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

// --- health + metrics ---------------------------------------------------

export type HealthStatus = {
  ok: boolean;
  nodes: number;
};

export type MetricSample = {
  name: string;
  labels: Record<string, string>;
  value: number;
};

export type MetricFamily = {
  name: string;
  help: string;
  type: "counter" | "gauge" | "histogram" | "summary" | "unknown";
  samples: MetricSample[];
};

export type MetricsSnapshot = {
  families: MetricFamily[];
  fetched_at: number;
};

// --- utility ------------------------------------------------------------

export type ApiError = {
  status: number;
  message: string;
  url: string;
};

// --- mission (Tier 1) --------------------------------------------------

export type MissionPriority = "escalate" | "sustain" | "wind_down";

export type MissionSignature = {
  casualty_density: number;
  immediate_fraction: number;
  unresolved_sector_fraction: number;
  medic_utilisation: number;
  time_budget_burn: number;
};

export type MissionStatus = {
  signature: MissionSignature;
  priority: MissionPriority | string;
  score: number;
  contributions: Record<string, number>;
  reasons: string[];
  medic_assignments: Record<string, string>;
  unresolved_regions: string[];
};

// --- twin (Tier 1) -----------------------------------------------------

export type TwinPosterior = {
  casualty_id: string;
  priority_probs: Record<string, number>;
  most_likely_priority: string;
  most_likely_probability: number;
  deterioration_rate: number;
  effective_sample_size: number;
  is_degenerate: boolean;
};

// --- forecast (Tier 1) -------------------------------------------------

export type CasualtyForecast = {
  casualty_id: string;
  score_history: number[];
  projected_score: number;
  projected_priority: string;
  slope_per_minute: number;
  confidence: number;
  reasons: string[];
  minutes_ahead: number;
};

export type MissionForecast = {
  projected_signature: MissionSignature;
  projected_priority: string;
  projected_score: number;
  contributions: Record<string, number>;
  per_channel_slope: Record<string, number>;
  reasons: string[];
  minutes_ahead: number;
};

// --- scorecard (Tier 1) ------------------------------------------------

export type Gate2PerClass = {
  precision: number;
  recall: number;
  f1: number;
  tp: number;
  fp: number;
  fn: number;
};

export type Gate2Summary = {
  accuracy: number;
  macro_f1: number;
  critical_miss_rate: number;
  per_class: Record<string, Gate2PerClass>;
  confusion_matrix: number[][];
  class_labels: string[];
};

export type CounterfactualCase = {
  casualty_id: string;
  severity: string;
  actual_priority: string;
  actual_outcome: number;
  counterfactuals: Record<string, number>;
  best_alternative: string;
  regret: number;
};

export type Scorecard = {
  gate2: Gate2Summary;
  counterfactuals: {
    cases: CounterfactualCase[];
    mean_regret: number;
    n: number;
  };
  summary: {
    total_casualties: number;
    critical_miss_rate: number;
    accuracy: number;
  };
};
