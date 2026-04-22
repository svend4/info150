// Simple CSV / JSON download helpers. Client-side only — no
// backend support needed. Triggers a file save through a temporary
// <a download> element.

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Free the URL once the browser has consumed it.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function downloadJson(data: unknown, filename: string): void {
  const text = JSON.stringify(data, null, 2);
  downloadBlob(new Blob([text], { type: "application/json" }), filename);
}

/**
 * Convert an array of flat records to CSV. Header = union of keys,
 * values are naive-stringified. Nested objects become JSON strings.
 */
export function downloadCsv(
  rows: readonly Record<string, unknown>[],
  filename: string,
): void {
  if (rows.length === 0) {
    downloadBlob(new Blob([""], { type: "text/csv" }), filename);
    return;
  }
  const headers = Array.from(
    rows.reduce((set, row) => {
      Object.keys(row).forEach((k) => set.add(k));
      return set;
    }, new Set<string>()),
  );
  const escape = (v: unknown): string => {
    if (v === null || v === undefined) return "";
    const s = typeof v === "object" ? JSON.stringify(v) : String(v);
    if (s.includes('"') || s.includes(",") || s.includes("\n")) {
      return `"${s.replace(/"/g, '""')}"`;
    }
    return s;
  };
  const lines = [
    headers.join(","),
    ...rows.map((row) => headers.map((h) => escape(row[h])).join(",")),
  ];
  downloadBlob(new Blob([lines.join("\n") + "\n"], { type: "text/csv" }), filename);
}
