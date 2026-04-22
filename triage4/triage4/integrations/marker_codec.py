"""Steganographic battlefield markers — offline casualty handoff.

Part of Phase 9e (speculative). When comms are denied and CRDT sync
isn't feasible, a medic can drop a physical marker (AR tag, QR code,
printed strip) on or near a casualty that encodes the core of their
``CasualtyNode``. The next responder scans the marker with any reader
and reconstructs the state without ever touching the network.

The encoded payload is an HMAC-signed JSON dict. HMAC ensures nobody
spoofs a marker or forges confident priorities; the shared secret is a
pre-mission key distributed to every medic tablet.

Design targets:
- triage4-only dependencies — pure stdlib (hmac, json, base64, hashlib);
- compact — typically ≤ 400 bytes per casualty in base64, well inside
  the 2 KB limit of QR version 10 at medium error correction;
- strict — any tamper (changed byte, wrong key, expired payload)
  raises ``InvalidMarker``.

Encode / decode go through ``MarkerPayload`` so only the essential
triage fields leave the tablet (no video / signatures / raw features).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import asdict, dataclass, field

from triage4.core.models import CasualtyNode, GeoPose, TraumaHypothesis


_ALGO = "sha256"
_VERSION = 1
_MAX_AGE_DEFAULT_S = 24 * 3600.0   # a day — longer = replay-abuse risk


class InvalidMarker(ValueError):
    """Raised when a marker fails signature / version / freshness checks."""


@dataclass
class MarkerPayload:
    """Minimal triage-relevant subset that goes into a marker."""

    casualty_id: str
    priority: str
    confidence: float
    x: float
    y: float
    z: float
    hypotheses: list[dict] = field(default_factory=list)   # [{kind, score}]
    status: str = "assessed"
    ts: float = 0.0
    medic: str | None = None
    version: int = _VERSION

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")
        if self.version != _VERSION:
            raise InvalidMarker(
                f"unsupported marker version {self.version} (expected {_VERSION})"
            )


def _canonical_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sign(payload_bytes: bytes, secret: bytes) -> bytes:
    return hmac.new(secret, payload_bytes, hashlib.sha256).digest()


def _payload_from_node(node: CasualtyNode, medic: str | None = None) -> MarkerPayload:
    return MarkerPayload(
        casualty_id=node.id,
        priority=node.triage_priority,
        confidence=round(float(node.confidence), 3),
        x=round(float(node.location.x), 2),
        y=round(float(node.location.y), 2),
        z=round(float(node.location.z), 2),
        hypotheses=[
            {"kind": h.kind, "score": round(float(h.score), 3)}
            for h in node.hypotheses[:3]  # top 3 — keep under QR budget
        ],
        status=node.status,
        ts=round(node.last_seen_ts, 3),
        medic=medic,
    )


def encode_marker(
    node: CasualtyNode,
    secret: bytes,
    medic: str | None = None,
    now_ts: float | None = None,
) -> bytes:
    """Return raw HMAC-signed JSON bytes. Best for binary transports."""
    if not isinstance(secret, (bytes, bytearray)) or len(secret) < 8:
        raise ValueError("secret must be bytes, at least 8 long")

    payload = _payload_from_node(node, medic=medic)
    if now_ts is not None:
        payload.ts = round(now_ts, 3)

    payload_dict = asdict(payload)
    payload_bytes = _canonical_bytes(payload_dict)
    sig = _sign(payload_bytes, secret)

    envelope = {
        "v": _VERSION,
        "alg": _ALGO,
        "payload": payload_dict,
        "sig": base64.b64encode(sig).decode("ascii"),
    }
    return _canonical_bytes(envelope)


def decode_marker(
    marker_bytes: bytes,
    secret: bytes,
    now_ts: float | None = None,
    max_age_s: float = _MAX_AGE_DEFAULT_S,
) -> MarkerPayload:
    """Verify HMAC, freshness, version; return a MarkerPayload."""
    if not isinstance(secret, (bytes, bytearray)) or len(secret) < 8:
        raise ValueError("secret must be bytes, at least 8 long")

    try:
        envelope = json.loads(marker_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidMarker(f"marker is not valid JSON: {exc}") from exc

    if envelope.get("v") != _VERSION:
        raise InvalidMarker(f"unsupported envelope version {envelope.get('v')}")
    if envelope.get("alg") != _ALGO:
        raise InvalidMarker(f"unsupported algorithm {envelope.get('alg')}")

    payload_dict = envelope.get("payload")
    provided_sig_b64 = envelope.get("sig")
    if not isinstance(payload_dict, dict) or not isinstance(provided_sig_b64, str):
        raise InvalidMarker("envelope missing payload or sig")

    provided_sig = base64.b64decode(provided_sig_b64)
    expected_sig = _sign(_canonical_bytes(payload_dict), secret)
    if not hmac.compare_digest(provided_sig, expected_sig):
        raise InvalidMarker("HMAC mismatch (tampered or wrong secret)")

    try:
        payload = MarkerPayload(**payload_dict)
    except TypeError as exc:
        raise InvalidMarker(f"payload shape invalid: {exc}") from exc

    if max_age_s > 0.0:
        reference = now_ts if now_ts is not None else time.time()
        if reference - payload.ts > max_age_s:
            raise InvalidMarker(
                f"marker is stale (age {reference - payload.ts:.1f}s > {max_age_s}s)"
            )

    return payload


def to_qr_string(marker_bytes: bytes) -> str:
    """URL-safe base64 — safe inside any QR code."""
    return base64.urlsafe_b64encode(marker_bytes).decode("ascii")


def from_qr_string(qr_text: str) -> bytes:
    padding = "=" * (-len(qr_text) % 4)
    return base64.urlsafe_b64decode((qr_text + padding).encode("ascii"))


def marker_to_node(payload: MarkerPayload) -> CasualtyNode:
    """Reconstruct a ``CasualtyNode`` from a decoded payload."""
    hypotheses = [
        TraumaHypothesis(kind=h["kind"], score=float(h["score"]))
        for h in payload.hypotheses
    ]
    return CasualtyNode(
        id=payload.casualty_id,
        location=GeoPose(x=payload.x, y=payload.y, z=payload.z),
        platform_source=f"marker:{payload.medic or 'unknown'}",
        confidence=payload.confidence,
        status=payload.status,
        hypotheses=hypotheses,
        triage_priority=payload.priority,
        first_seen_ts=payload.ts,
        last_seen_ts=payload.ts,
        assigned_medic=payload.medic,
    )
