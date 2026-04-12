from cortex.verification.verifier import SovereignVerifier


def test_ouroboros_invariants_extraction():
    verifier = SovereignVerifier()

    # 1. Test I8 (MEV Bundle Detection)
    mev_code = """
def execute_arb():
    from jito_bundle import JitoBundler
    bundler = JitoBundler()
    bundle = bundler.build_bundle(slots)
    return bundle
"""
    res_mev = verifier.check(mev_code, {"file_path": "mev_strategy.py"})
    assert res_mev.is_valid is False
    assert any(v["id"] == "I8" for v in res_mev.violations)
    print("✅ I8 (MEV) Invariant Verification PASS")

    # 2. Test I9 (Proxy Signal Loss - Violation)
    proxy_fail_code = """
def compress():
    return collapse_context(prompt, signal_loss=0.35)
"""
    res_proxy_fail = verifier.check(proxy_fail_code, {"file_path": "proxy_config.py"})
    assert res_proxy_fail.is_valid is False
    assert any(v["id"] == "I9" for v in res_proxy_fail.violations)
    print("✅ I9 (Proxy Fail) Invariant Verification PASS")

    # 3. Test I9 (Proxy Signal Loss - Safe)
    proxy_safe_code = """
def compress():
    return collapse_context(prompt, signal_loss=0.15)
"""
    res_proxy_safe = verifier.check(proxy_safe_code, {"file_path": "proxy_config.py"})
    # Since only I9 is relevant here and it's within limits
    assert res_proxy_safe.is_valid is True
    print("✅ I9 (Proxy Safe) Invariant Verification PASS")


if __name__ == "__main__":
    test_ouroboros_invariants_extraction()
