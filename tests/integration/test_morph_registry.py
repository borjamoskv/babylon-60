def test_registry_records_snapshot(registry):
    snap = registry.record_snapshot("AGENTS", {"c": 1})
    assert snap.snapshot_id is not None
    assert snap.prev_hash is None

def test_registry_chain_links(registry):
    s1 = registry.record_snapshot("AGENTS_1", {})
    s2 = registry.record_snapshot("AGENTS_2", {})
    assert s2.prev_hash == s1.snapshot_id

def test_current_snapshot_returns_latest(registry):
    assert registry.current_snapshot() is None
    registry.record_snapshot("AGENTS", {})
    assert registry.current_snapshot() is not None
