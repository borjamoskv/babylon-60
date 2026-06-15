def test_divergence_no_diff(auditor):
    exp = {"routes": {"a": "sig_a"}, "capabilities": ["c1"]}
    act = {"routes": {"a": "sig_a"}, "capabilities": ["c1"]}
    report = auditor.build_report("a1", "obs_fp", "exp_fp", exp, act, 1.0)
    assert not report.route_deltas
    assert report.severity == "ok"

def test_divergence_missing_route(auditor):
    exp = {"routes": {"a": "sig_a", "b": "sig_b"}}
    act = {"routes": {"a": "sig_a"}}
    report = auditor.build_report("a1", "obs", "exp", exp, act, 1.0)
    assert any(d["type"] == "missing_route" and d["route"] == "b" for d in report.route_deltas)
    assert report.severity == "high"

def test_divergence_signature_mismatch(auditor):
    exp = {"routes": {"a": "sig_a"}}
    act = {"routes": {"a": "sig_b"}}
    report = auditor.build_report("a1", "obs", "exp", exp, act, 1.0)
    assert any(d["type"] == "route_signature_mismatch" and d["route"] == "a" for d in report.route_deltas)
    assert report.severity == "high"
