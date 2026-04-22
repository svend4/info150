// Display-formatting helpers. Pure.

export function formatPercent(v: number, fractionDigits = 0): string {
  if (!Number.isFinite(v)) return "—";
  return `${(v * 100).toFixed(fractionDigits)}%`;
}

export function formatConfidence(v: number): string {
  return formatPercent(v, 0);
}

export function formatScore(v: number): string {
  if (!Number.isFinite(v)) return "—";
  return v.toFixed(2);
}

export function formatCoord(v: number): string {
  if (!Number.isFinite(v)) return "—";
  return v.toFixed(1);
}

export function formatAge(ts: number | null): string {
  if (ts === null) return "never";
  const seconds = Math.floor((Date.now() - ts) / 1000);
  if (seconds < 2) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

export function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
