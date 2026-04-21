from triage4.state_graph.evidence_memory import EvidenceMemory


def test_record_and_events_for_casualty():
    mem = EvidenceMemory()
    mem.record("detection", "C1", {"score": 0.9}, ts=1.0)
    mem.record("detection", "C2", {"score": 0.8}, ts=2.0)
    mem.record("assessment", "C1", {"priority": "immediate"}, ts=3.0)

    assert len(mem) == 3
    c1 = mem.events_for("C1")
    assert [e.kind for e in c1] == ["detection", "assessment"]


def test_causal_chain_walks_backward():
    mem = EvidenceMemory()
    a = mem.record("detection", "C1", ts=1.0)
    b = mem.record("signature", "C1", ts=2.0, causes=[a])
    c = mem.record("assessment", "C1", ts=3.0, causes=[b])

    chain = mem.causal_chain(c)
    assert chain == [a, b]


def test_snapshots_are_immutable():
    mem = EvidenceMemory()
    mem.record("detection", "C1", {"x": 1}, ts=1.0)
    mem.snapshot("checkpoint")

    mem.record("assessment", "C1", {"priority": "immediate"}, ts=2.0)

    snap = mem.load_snapshot("checkpoint")
    assert snap is not None
    assert len(snap["events"]) == 1
    assert len(mem) == 2  # live memory kept growing
