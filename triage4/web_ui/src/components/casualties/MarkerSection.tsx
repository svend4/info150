// Offline marker section: HMAC-signed QR-safe payload for physical
// handoff. Shown inside HandoffPanel as a collapsible section.
// The frontend doesn't render the actual QR image — that's left to
// whatever QR reader/printer the operator has on hand. Clipboard
// copy + byte-size info are exposed so the operator can verify the
// payload fits their QR encoder's budget.

import { useState } from "react";

import { fetchMarker } from "../../api/endpoints";
import { useResource } from "../../hooks/useResource";

type Props = { casualtyId: string };

export default function MarkerSection({ casualtyId }: Props) {
  const { data, error, loading } = useResource(
    (signal) => fetchMarker(casualtyId, signal),
    [casualtyId],
  );
  const [copied, setCopied] = useState(false);

  if (loading && !data) {
    return (
      <div style={{ color: "var(--text-2)", fontStyle: "italic", fontSize: 12 }}>
        generating marker…
      </div>
    );
  }
  if (error) {
    return (
      <div style={{ color: "var(--err)", fontSize: 12 }}>{error.message}</div>
    );
  }
  if (!data) return null;

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(data.qr_payload);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard not available in insecure contexts — no-op */
    }
  };

  // Heuristic fit indicator — QR version 10 at medium ECC stores
  // roughly 213 bytes; anything below that fits comfortably on a
  // printed tag the size of a playing card.
  const withinV10 = data.qr_chars < 480;

  // External QR preview service — no network request is issued from
  // the frontend until the user clicks the link. Keeps the dashboard
  // offline-capable by default.
  const previewUrl = `https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(data.qr_payload)}`;

  return (
    <div
      style={{
        padding: 12,
        background: "var(--bg-1)",
        border: "1px solid var(--border-1)",
        borderRadius: "var(--r2)",
        marginTop: 12,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 8,
        }}
      >
        <h4
          style={{
            margin: 0,
            fontSize: 13,
            letterSpacing: 1,
            textTransform: "uppercase",
            color: "var(--text-2)",
          }}
        >
          offline marker (HMAC-signed)
        </h4>
        <div style={{ fontSize: 11, color: "var(--text-2)" }}>
          {data.envelope_bytes} B envelope · {data.qr_chars} QR chars{" "}
          <span
            style={{
              marginLeft: 4,
              color: withinV10 ? "var(--ok)" : "var(--warn)",
              fontWeight: 600,
            }}
          >
            {withinV10 ? "✓ fits QR v10" : "⚠ exceeds QR v10"}
          </span>
        </div>
      </div>
      <pre
        style={{
          fontSize: 10,
          maxHeight: 120,
          wordBreak: "break-all",
          whiteSpace: "pre-wrap",
        }}
      >
        {data.qr_payload}
      </pre>
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button onClick={onCopy}>
          {copied ? "copied ✓" : "copy marker"}
        </button>
        <a
          href={previewUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            display: "inline-block",
            padding: "6px 12px",
            fontSize: 13,
            background: "var(--bg-2)",
            border: "1px solid var(--border-1)",
            borderRadius: "var(--r1)",
          }}
        >
          preview QR (external service)
        </a>
      </div>
      <div
        style={{
          marginTop: 8,
          fontSize: 11,
          color: "var(--text-2)",
        }}
      >
        Payload is base64-urlsafe of an HMAC-SHA256 envelope. Offline
        readers (QR scanner + triage4 decoder) verify freshness +
        signature. External preview link sends the payload to
        api.qrserver.com — do not use for any real casualty id.
      </div>
    </div>
  );
}
