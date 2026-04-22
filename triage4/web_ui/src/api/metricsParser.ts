// Prometheus text-exposition-format parser (spec v0.0.4).
//
// Minimal, stdlib-only. Handles the metrics our backend emits:
// counter, gauge, histogram. Not a full spec-compliant parser —
// good enough for the /metrics endpoint contract in
// triage4/ui/metrics.py.

import type { MetricFamily, MetricSample, MetricsSnapshot } from "../types";

type MetricType = MetricFamily["type"];

const VALID_TYPES: MetricType[] = ["counter", "gauge", "histogram", "summary"];

function parseLabels(raw: string): Record<string, string> {
  const out: Record<string, string> = {};
  if (!raw) return out;
  // Strip surrounding { } if present.
  const trimmed = raw.replace(/^\{/, "").replace(/\}$/, "").trim();
  if (!trimmed) return out;

  // Naive splitter: Prometheus label values can contain commas
  // only when escaped with backslash. We treat labels conservatively
  // — they're simple in our backend.
  const parts = trimmed.split(",");
  for (const part of parts) {
    const eq = part.indexOf("=");
    if (eq === -1) continue;
    const key = part.slice(0, eq).trim();
    let value = part.slice(eq + 1).trim();
    if (value.startsWith('"') && value.endsWith('"')) {
      value = value.slice(1, -1);
    }
    if (key) out[key] = value;
  }
  return out;
}

function parseSampleLine(line: string): MetricSample | null {
  // Format: <name>{<labels>} <value>  OR  <name> <value>
  const openBrace = line.indexOf("{");
  let name: string;
  let labelsRaw: string;
  let valueRaw: string;

  if (openBrace !== -1) {
    const closeBrace = line.indexOf("}", openBrace);
    if (closeBrace === -1) return null;
    name = line.slice(0, openBrace).trim();
    labelsRaw = line.slice(openBrace, closeBrace + 1);
    valueRaw = line.slice(closeBrace + 1).trim();
  } else {
    const firstSpace = line.indexOf(" ");
    if (firstSpace === -1) return null;
    name = line.slice(0, firstSpace).trim();
    labelsRaw = "";
    valueRaw = line.slice(firstSpace + 1).trim();
  }

  const firstToken = valueRaw.split(/\s+/)[0];
  const value = parseFloat(firstToken);
  if (!Number.isFinite(value)) return null;

  return {
    name,
    labels: parseLabels(labelsRaw),
    value,
  };
}

export function parseMetrics(text: string): MetricsSnapshot {
  const families = new Map<string, MetricFamily>();
  const lines = text.split("\n");

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line) continue;

    if (line.startsWith("# HELP ")) {
      const rest = line.slice("# HELP ".length);
      const firstSpace = rest.indexOf(" ");
      if (firstSpace === -1) continue;
      const name = rest.slice(0, firstSpace);
      const help = rest.slice(firstSpace + 1);
      const current = families.get(name) ?? {
        name,
        help: "",
        type: "unknown" as MetricType,
        samples: [],
      };
      current.help = help;
      families.set(name, current);
      continue;
    }

    if (line.startsWith("# TYPE ")) {
      const rest = line.slice("# TYPE ".length);
      const [name, typeRaw] = rest.split(/\s+/);
      if (!name || !typeRaw) continue;
      const kind = VALID_TYPES.includes(typeRaw as MetricType)
        ? (typeRaw as MetricType)
        : ("unknown" as MetricType);
      const current = families.get(name) ?? {
        name,
        help: "",
        type: kind,
        samples: [],
      };
      current.type = kind;
      families.set(name, current);
      continue;
    }

    if (line.startsWith("#")) continue;

    const sample = parseSampleLine(line);
    if (!sample) continue;

    // For histograms the sample name includes _bucket / _sum / _count
    // suffixes; we attribute those to the parent family.
    const parentName = sample.name.replace(/_(bucket|sum|count)$/, "");
    const fam = families.get(parentName) ?? families.get(sample.name) ?? {
      name: parentName,
      help: "",
      type: "unknown" as MetricType,
      samples: [],
    };
    fam.samples.push(sample);
    families.set(fam.name, fam);
  }

  return {
    families: Array.from(families.values()).sort((a, b) =>
      a.name.localeCompare(b.name),
    ),
    fetched_at: Date.now(),
  };
}

export function pickCounterByLabel(
  family: MetricFamily | undefined,
  label: string,
  value: string,
): number {
  if (!family) return 0;
  const hit = family.samples.find((s) => s.labels[label] === value);
  return hit?.value ?? 0;
}

export function summariseHistogram(family: MetricFamily | undefined): {
  count: number;
  sum: number;
  avg: number;
  buckets: { le: number | "+Inf"; count: number }[];
} {
  if (!family) return { count: 0, sum: 0, avg: 0, buckets: [] };
  const count =
    family.samples.find((s) => s.name.endsWith("_count"))?.value ?? 0;
  const sum = family.samples.find((s) => s.name.endsWith("_sum"))?.value ?? 0;
  const avg = count > 0 ? sum / count : 0;
  const buckets = family.samples
    .filter((s) => s.name.endsWith("_bucket"))
    .map((s) => {
      const le = s.labels["le"];
      return {
        le: le === "+Inf" ? ("+Inf" as const) : Number(le),
        count: s.value,
      };
    })
    .sort((a, b) => {
      if (a.le === "+Inf") return 1;
      if (b.le === "+Inf") return -1;
      return (a.le as number) - (b.le as number);
    });
  return { count, sum, avg, buckets };
}
