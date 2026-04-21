export function priorityColor(priority: string): string {
  if (priority === "immediate") return "#ff5c5c";
  if (priority === "delayed") return "#ffb84d";
  if (priority === "minimal") return "#63d471";
  return "#a0aec0";
}

export function scaleCoord(v: number): number {
  return v * 5;
}
