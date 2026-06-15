def test_bridge_compilation(bridge_compiler):
    exp = {"route": "cmd", "params": ["a", "b"]}
    act = {"route": "cmd", "params": ["a"]}
    artifact = bridge_compiler.compile_bridge("agent1", exp, act)
    assert artifact.bridge_id is not None
    assert "kwargs.get(\"b\", None)" in artifact.adapter_code
    assert "kwargs.get(\"a\")" in artifact.adapter_code
