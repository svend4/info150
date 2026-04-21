export type Casualty = {
  id: string;
  triage_priority: string;
  confidence: number;
  platform_source: string;
  location: { x: number; y: number; z: number };
  hypotheses: { kind: string; score: number; explanation: string }[];
  signatures: {
    bleeding_visual_score: number;
    perfusion_drop_score: number;
    chest_motion_fd: number;
    body_region_polygons?: Record<string, [number, number][]>;
    raw_features?: Record<string, number>;
  };
};

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

export type ReplayData = {
  frames: ReplayFrame[];
};
