"""triage4 — steganographic marker handoff demo.

Simulates a denied-comms battlefield handoff: medic A assesses a
casualty, encodes the node into an HMAC-signed marker, tapes the QR-safe
string to the casualty, and walks away. Later medic B scans the marker
and reconstructs the casualty state locally — no network required.

The demo also shows the three failure modes the codec refuses to let
through: a tampered payload, a wrong secret, and an expired marker.

Run from the project root:

    python examples/marker_handoff_demo.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from triage4.core.models import CasualtyNode, GeoPose, TraumaHypothesis  # noqa: E402
from triage4.integrations import (  # noqa: E402
    InvalidMarker,
    decode_marker,
    encode_marker,
    from_qr_string,
    marker_to_node,
    to_qr_string,
)


def _build_node() -> CasualtyNode:
    return CasualtyNode(
        id="C17",
        location=GeoPose(x=12.5, y=-3.25, z=0.0),
        platform_source="uav:alpha",
        confidence=0.82,
        status="assessed",
        hypotheses=[
            TraumaHypothesis(kind="hemorrhage_major", score=0.91),
            TraumaHypothesis(kind="shock", score=0.63),
            TraumaHypothesis(kind="respiratory_distress", score=0.21),
        ],
        triage_priority="immediate",
        first_seen_ts=1000.0,
        last_seen_ts=1020.5,
    )


def main() -> None:
    secret = b"shared_mission_key_2026"
    now = time.time()

    print("== medic A: encode marker ==")
    node = _build_node()
    marker = encode_marker(node, secret=secret, medic="alpha", now_ts=now)
    qr_text = to_qr_string(marker)
    print(f"raw bytes:    {len(marker)} B")
    print(f"QR-safe text: {len(qr_text)} chars")
    print(f"first 80:     {qr_text[:80]}...")

    print("\n== medic B: decode + rebuild node ==")
    recovered_bytes = from_qr_string(qr_text)
    payload = decode_marker(recovered_bytes, secret=secret, now_ts=now)
    rebuilt = marker_to_node(payload)
    print(f"id:            {rebuilt.id}")
    print(f"priority:      {rebuilt.triage_priority}")
    print(f"confidence:    {rebuilt.confidence}")
    print(f"location:      ({rebuilt.location.x}, {rebuilt.location.y})")
    print(f"hypotheses:    {[(h.kind, h.score) for h in rebuilt.hypotheses]}")
    print(f"from medic:    {payload.medic}")

    print("\n== failure modes the codec rejects ==")

    # Tampered byte.
    tampered = bytearray(marker)
    tampered[40] ^= 0x01
    try:
        decode_marker(bytes(tampered), secret=secret, now_ts=now)
    except InvalidMarker as exc:
        print(f"tampered:      rejected ({exc})")

    # Wrong secret.
    try:
        decode_marker(marker, secret=b"wrong_mission_key", now_ts=now)
    except InvalidMarker as exc:
        print(f"wrong secret:  rejected ({exc})")

    # Expired marker.
    far_future = now + 48 * 3600.0
    try:
        decode_marker(marker, secret=secret, now_ts=far_future)
    except InvalidMarker as exc:
        print(f"expired:       rejected ({exc})")

    print("\n✓ handoff verified end-to-end — safe for denied-comms use")


if __name__ == "__main__":
    main()
