"""Property-based tests (hypothesis).

Covers three surfaces where algebraic invariants matter:

- **CRDT merges** — commutative, idempotent, associative. Re-proved
  empirically across randomised event histories.
- **Marker codec** — encode/decode roundtrip + rejection of any
  byte-level tampering.
- **Score fusion** — monotonicity under channel increase on the
  critical direction.

These complement, not replace, the hand-written regression tests.
"""

from __future__ import annotations

import copy

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from triage4.core.models import CasualtyNode, CasualtySignature, GeoPose
from triage4.integrations.marker_codec import (
    InvalidMarker,
    decode_marker,
    encode_marker,
    from_qr_string,
    marker_to_node,
    to_qr_string,
)
from triage4.state_graph.crdt_graph import CRDTCasualtyGraph
from triage4.triage_reasoning.score_fusion import fuse_triage_score


# Shared settings: property tests are small (~50 cases) so the total
# suite stays sub-5 s.
_SETTINGS = settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


# Hypothesis strategies ------------------------------------------------

_priority_st = st.sampled_from(["immediate", "delayed", "minimal", "unknown"])
_casualty_id_st = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=1, max_size=6,
)
_replica_id_st = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    min_size=1, max_size=4,
)
_timestamp_st = st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False)
_score_channel_st = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


@st.composite
def _crdt_event_list(draw):
    """A random sequence of events to replay on a replica."""
    n = draw(st.integers(min_value=0, max_value=20))
    events = []
    for _ in range(n):
        kind = draw(st.sampled_from(["add", "set_priority", "observe", "remove"]))
        cid = draw(_casualty_id_st)
        if kind == "add":
            events.append(("add", cid))
        elif kind == "set_priority":
            prio = draw(_priority_st)
            ts = draw(_timestamp_st)
            events.append(("set_priority", cid, prio, ts))
        elif kind == "observe":
            events.append(("observe", cid))
        elif kind == "remove":
            events.append(("remove", cid))
    return events


def _apply_events(replica: CRDTCasualtyGraph, events: list[tuple]) -> None:
    for ev in events:
        if ev[0] == "add":
            replica.add_casualty(ev[1])
        elif ev[0] == "set_priority":
            replica.set_priority(ev[1], ev[2], ts=ev[3])
        elif ev[0] == "observe":
            if ev[1] in replica.casualty_ids:
                replica.increment_observation(ev[1])
        elif ev[0] == "remove":
            replica.remove_casualty(ev[1])


# CRDT merge algebra ---------------------------------------------------


@_SETTINGS
@given(events_a=_crdt_event_list(), events_b=_crdt_event_list())
def test_crdt_merge_is_commutative(events_a, events_b):
    """A.merge(B) then observe == B.merge(A) then observe."""
    a1 = CRDTCasualtyGraph(replica_id="A")
    b1 = CRDTCasualtyGraph(replica_id="B")
    _apply_events(a1, events_a)
    _apply_events(b1, events_b)

    left = copy.deepcopy(a1)
    left.merge(b1)
    right = copy.deepcopy(b1)
    right.merge(a1)

    assert left.casualty_ids == right.casualty_ids
    for cid in left.casualty_ids:
        assert left.get_priority(cid) == right.get_priority(cid)
        assert left.observation_count(cid) == right.observation_count(cid)


@_SETTINGS
@given(events_a=_crdt_event_list(), events_b=_crdt_event_list())
def test_crdt_merge_is_idempotent(events_a, events_b):
    """merge(B) once == merge(B) twice."""
    a = CRDTCasualtyGraph(replica_id="A")
    b = CRDTCasualtyGraph(replica_id="B")
    _apply_events(a, events_a)
    _apply_events(b, events_b)

    once = copy.deepcopy(a)
    once.merge(b)

    twice = copy.deepcopy(a)
    twice.merge(b)
    twice.merge(b)

    assert once.casualty_ids == twice.casualty_ids
    for cid in once.casualty_ids:
        assert once.get_priority(cid) == twice.get_priority(cid)
        assert once.observation_count(cid) == twice.observation_count(cid)


@_SETTINGS
@given(
    events_a=_crdt_event_list(),
    events_b=_crdt_event_list(),
    events_c=_crdt_event_list(),
)
def test_crdt_merge_is_associative(events_a, events_b, events_c):
    """(A.merge(B)).merge(C) == A.merge(B.merge(C))."""
    def _fresh(events, rid):
        r = CRDTCasualtyGraph(replica_id=rid)
        _apply_events(r, events)
        return r

    left = _fresh(events_a, "A")
    left.merge(_fresh(events_b, "B"))
    left.merge(_fresh(events_c, "C"))

    right = _fresh(events_a, "A")
    mid = _fresh(events_b, "B")
    mid.merge(_fresh(events_c, "C"))
    right.merge(mid)

    assert left.casualty_ids == right.casualty_ids
    for cid in left.casualty_ids:
        assert left.get_priority(cid) == right.get_priority(cid)
        assert left.observation_count(cid) == right.observation_count(cid)


# Marker codec ---------------------------------------------------------


@st.composite
def _marker_node(draw):
    return CasualtyNode(
        id=draw(_casualty_id_st),
        location=GeoPose(
            x=draw(st.floats(min_value=-1e4, max_value=1e4, allow_nan=False)),
            y=draw(st.floats(min_value=-1e4, max_value=1e4, allow_nan=False)),
            z=draw(st.floats(min_value=-1e3, max_value=1e3, allow_nan=False)),
        ),
        platform_source="test",
        confidence=draw(_score_channel_st),
        status="assessed",
        triage_priority=draw(_priority_st),
        first_seen_ts=draw(_timestamp_st),
        last_seen_ts=draw(_timestamp_st),
    )


_secret_st = st.binary(min_size=8, max_size=64)


@_SETTINGS
@given(node=_marker_node(), secret=_secret_st, now=_timestamp_st)
def test_marker_encode_decode_roundtrip(node, secret, now):
    envelope = encode_marker(node, secret=secret, medic="alpha", now_ts=now)
    payload = decode_marker(envelope, secret=secret, now_ts=now)
    assert payload.casualty_id == node.id
    assert payload.priority == node.triage_priority
    rebuilt = marker_to_node(payload)
    assert rebuilt.id == node.id
    assert rebuilt.triage_priority == node.triage_priority


@_SETTINGS
@given(node=_marker_node(), secret=_secret_st, now=_timestamp_st)
def test_marker_qr_roundtrip_preserves_bytes(node, secret, now):
    envelope = encode_marker(node, secret=secret, now_ts=now)
    qr = to_qr_string(envelope)
    assert from_qr_string(qr) == envelope


@_SETTINGS
@given(
    node=_marker_node(),
    secret=_secret_st,
    now=_timestamp_st,
    flip_pos=st.integers(min_value=0, max_value=1000),
)
def test_marker_any_single_byte_flip_is_rejected(node, secret, now, flip_pos):
    envelope = bytearray(encode_marker(node, secret=secret, now_ts=now))
    pos = flip_pos % len(envelope)
    envelope[pos] ^= 0x01
    with pytest.raises(InvalidMarker):
        decode_marker(bytes(envelope), secret=secret, now_ts=now)


@_SETTINGS
@given(
    node=_marker_node(),
    secret_a=_secret_st,
    secret_b=_secret_st,
    now=_timestamp_st,
)
def test_marker_wrong_secret_is_rejected(node, secret_a, secret_b, now):
    if secret_a == secret_b:
        return  # degenerate — same key, can't test mismatch
    envelope = encode_marker(node, secret=secret_a, now_ts=now)
    with pytest.raises(InvalidMarker):
        decode_marker(envelope, secret=secret_b, now_ts=now)


# Score fusion monotonicity --------------------------------------------


def _sig_with_bleeding(x: float) -> CasualtySignature:
    return CasualtySignature(
        bleeding_visual_score=x,
        perfusion_drop_score=0.1,
        posture_instability_score=0.1,
        thermal_asymmetry_score=0.1,
        chest_motion_fd=0.5,
        breathing_curve=[0.2] * 6,
    )


@_SETTINGS
@given(
    low=st.floats(min_value=0.0, max_value=0.5, allow_nan=False),
    delta=st.floats(min_value=0.01, max_value=0.5, allow_nan=False),
)
def test_bleeding_increase_monotonically_raises_urgency_or_same(low, delta):
    """Increasing bleeding cannot lower the fused score — same priority
    band or strictly higher.

    Bleeding is a positive-urgency channel; fuse_triage_score must be
    non-decreasing in it, holding other channels constant.
    """
    high = min(1.0, low + delta)

    sig_low = _sig_with_bleeding(low)
    sig_high = _sig_with_bleeding(high)

    score_low = fuse_triage_score(sig_low).score
    score_high = fuse_triage_score(sig_high).score

    assert score_high >= score_low - 1e-9


@_SETTINGS
@given(
    low=st.floats(min_value=0.0, max_value=0.5, allow_nan=False),
    delta=st.floats(min_value=0.01, max_value=0.5, allow_nan=False),
)
def test_score_vector_is_in_unit_interval(low, delta):
    """Fused score must stay in [0, 1] for any convex input."""
    high = min(1.0, low + delta)
    for x in (low, high):
        sig = _sig_with_bleeding(x)
        score = fuse_triage_score(sig).score
        assert 0.0 <= score <= 1.0
