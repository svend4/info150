// Typed helpers for every backend endpoint the dashboard uses.
//
// Single source of truth for URL paths — no string literals in
// components. Keeps the UI resilient to backend routing changes.

import type {
  Casualty,
  CasualtyForecast,
  ConflictReport,
  Explanation,
  GraphData,
  HandoffPayload,
  HealthStatus,
  MapData,
  MarkerInfo,
  MissionForecast,
  MissionStatus,
  Overview,
  ReplayData,
  Scorecard,
  SecondOpinion,
  SensingResult,
  SkeletalSnapshot,
  TaskRecommendation,
  TwinPosterior,
  UncertaintyReport,
} from "../types";
import { getJson, getText } from "./client";

export function fetchHealth(signal?: AbortSignal): Promise<HealthStatus> {
  return getJson<HealthStatus>("/health", signal);
}

export function fetchCasualties(signal?: AbortSignal): Promise<Casualty[]> {
  return getJson<Casualty[]>("/casualties", signal);
}

export function fetchCasualty(id: string, signal?: AbortSignal): Promise<Casualty> {
  return getJson<Casualty>(`/casualties/${encodeURIComponent(id)}`, signal);
}

export function fetchExplanation(id: string, signal?: AbortSignal): Promise<Explanation> {
  return getJson<Explanation>(`/casualties/${encodeURIComponent(id)}/explain`, signal);
}

export function fetchHandoff(id: string, signal?: AbortSignal): Promise<HandoffPayload> {
  return getJson<HandoffPayload>(`/casualties/${encodeURIComponent(id)}/handoff`, signal);
}

export function fetchTasks(signal?: AbortSignal): Promise<TaskRecommendation[]> {
  return getJson<TaskRecommendation[]>("/tasks", signal);
}

export function fetchMap(signal?: AbortSignal): Promise<MapData> {
  return getJson<MapData>("/map", signal);
}

export function fetchReplay(signal?: AbortSignal): Promise<ReplayData> {
  return getJson<ReplayData>("/replay", signal);
}

export function fetchGraph(signal?: AbortSignal): Promise<GraphData> {
  return getJson<GraphData>("/graph", signal);
}

export function fetchMetricsText(signal?: AbortSignal): Promise<string> {
  return getText("/metrics", signal);
}

// Tier 1 — new endpoints.

export function fetchMissionStatus(signal?: AbortSignal): Promise<MissionStatus> {
  return getJson<MissionStatus>("/mission/status", signal);
}

export function fetchCasualtyTwin(
  id: string,
  signal?: AbortSignal,
): Promise<TwinPosterior> {
  return getJson<TwinPosterior>(
    `/casualties/${encodeURIComponent(id)}/twin`,
    signal,
  );
}

export function fetchCasualtyForecast(
  id: string,
  minutes: number,
  signal?: AbortSignal,
): Promise<CasualtyForecast> {
  return getJson<CasualtyForecast>(
    `/forecast/casualty/${encodeURIComponent(id)}?minutes=${minutes}`,
    signal,
  );
}

export function fetchMissionForecast(
  minutes: number,
  signal?: AbortSignal,
): Promise<MissionForecast> {
  return getJson<MissionForecast>(`/forecast/mission?minutes=${minutes}`, signal);
}

export function fetchScorecard(signal?: AbortSignal): Promise<Scorecard> {
  return getJson<Scorecard>("/evaluation/scorecard", signal);
}

// Tier 2 — second-opinion / uncertainty / conflict resolver.

export function fetchSecondOpinion(
  id: string,
  signal?: AbortSignal,
): Promise<SecondOpinion> {
  return getJson<SecondOpinion>(
    `/casualties/${encodeURIComponent(id)}/second-opinion`,
    signal,
  );
}

export function fetchUncertainty(
  id: string,
  signal?: AbortSignal,
): Promise<UncertaintyReport> {
  return getJson<UncertaintyReport>(
    `/casualties/${encodeURIComponent(id)}/uncertainty`,
    signal,
  );
}

export function fetchConflict(
  id: string,
  signal?: AbortSignal,
): Promise<ConflictReport> {
  return getJson<ConflictReport>(
    `/casualties/${encodeURIComponent(id)}/conflict`,
    signal,
  );
}

// Tier 3 — overview + marker.

export function fetchOverview(signal?: AbortSignal): Promise<Overview> {
  return getJson<Overview>("/overview", signal);
}

export function fetchMarker(
  id: string,
  signal?: AbortSignal,
): Promise<MarkerInfo> {
  return getJson<MarkerInfo>(
    `/casualties/${encodeURIComponent(id)}/marker`,
    signal,
  );
}

// Final — skeletal graph + active sensing.

export function fetchSkeletal(
  id: string,
  signal?: AbortSignal,
): Promise<SkeletalSnapshot> {
  return getJson<SkeletalSnapshot>(
    `/casualties/${encodeURIComponent(id)}/skeletal`,
    signal,
  );
}

export function fetchSensingRanked(
  topK?: number,
  signal?: AbortSignal,
): Promise<SensingResult> {
  const qs = topK !== undefined ? `?top_k=${topK}` : "";
  return getJson<SensingResult>(`/sensing/ranked${qs}`, signal);
}
