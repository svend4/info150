// Priority → display colour. Kept backward-compatible with the
// original minimal dashboard.

export function priorityColor(priority: string): string {
  if (priority === "immediate") return "#ff5c5c";
  if (priority === "delayed") return "#ffb84d";
  if (priority === "minimal") return "#63d471";
  if (priority === "expectant") return "#c678dd";
  return "#a0aec0";
}

export function priorityBackground(priority: string): string {
  // Dimmed variant for hover / selection backgrounds.
  if (priority === "immediate") return "#3a1a1a";
  if (priority === "delayed") return "#3a2a10";
  if (priority === "minimal") return "#1a3320";
  if (priority === "expectant") return "#2a1f36";
  return "#1a1f30";
}

export function scaleCoord(v: number): number {
  return v * 5;
}
