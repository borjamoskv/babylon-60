import logging

from cortex.verification.verifier import SovereignVerifier

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TEST.VERIFIER")


def test_runtime_verification():
    verifier = SovereignVerifier()

    # 1. Test Success
    print("\n--- STEP 1: Verification of SUCCESS (exit 0) ---")
    status_ok = {"exit_code": 0, "stdout": "Test passed", "stderr": ""}
    res_ok = verifier.verify_runtime("cmd_001", status_ok)
    print(f"Result OK: {res_ok.runtime_status} (is_valid: {res_ok.is_valid})")
    assert res_ok.is_valid is True
    assert res_ok.runtime_status == "SUCCESS"

    # 2. Test Failure (Quarantine)
    print("\n--- STEP 2: Verification of FAILURE (exit 1) ---")
    status_fail = {"exit_code": 1, "stdout": "Partial run", "stderr": "Error: Segmentation fault"}
    res_fail = verifier.verify_runtime("cmd_002", status_fail)
    print(f"Result FAIL: {res_fail.runtime_status} (is_valid: {res_fail.is_valid})")
    assert res_fail.is_valid is False
    assert res_fail.runtime_status == "QUARANTINED"
    assert res_fail.violations[0]["id"] == "V-ERR-01"

    print("\n✅ C5-REAL Runtime Verification CERTIFIED.")


if __name__ == "__main__":
    test_runtime_verification()
