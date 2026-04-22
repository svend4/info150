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
