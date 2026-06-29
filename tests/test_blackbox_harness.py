# [C5-REAL] Exergy-Maximized

from babylon60.tools.blackbox_harness import PassiveFingerprintAnalyzer, SingleResult

def test_empty_results():
    analyzer = PassiveFingerprintAnalyzer([])
    classification = analyzer.classify()
    assert classification["predicted_family"] == "Unknown"
    assert classification["confidence"] == 0.0

def test_claude_classification():
    # Target: itl = 22.0, ratio = 3.8, md_density = 0.12
    run = SingleResult(
        prompt_sha256="abc",
        status_code=200,
        rejected=False,
        error_type=None,
        latency_ms=1100.0,
        ttft_ms=0.0,
        completion_tokens=50,
        tokens_per_sec=45.45,
        json_valid=False,
        exact_match=None,
        response_preview="#" * 23 + "a" * 167,
        timestamp_iso="2026-06-29"
    )
    analyzer = PassiveFingerprintAnalyzer([run])
    classification = analyzer.classify()
    assert classification["predicted_family"] == "Claude_3_5_Sonnet"
    assert classification["confidence"] > 0.45

def test_gpt_classification():
    # Target: itl = 10.0, ratio = 4.2, md_density = 0.05
    run = SingleResult(
        prompt_sha256="def",
        status_code=200,
        rejected=False,
        error_type=None,
        latency_ms=500.0,
        ttft_ms=0.0,
        completion_tokens=50,
        tokens_per_sec=100.0,
        json_valid=False,
        exact_match=None,
        response_preview="#" * 10 + "a" * 200,
        timestamp_iso="2026-06-29"
    )
    analyzer = PassiveFingerprintAnalyzer([run])
    classification = analyzer.classify()
    assert classification["predicted_family"] == "GPT_4o"
    assert classification["confidence"] > 0.45

def test_gemini_classification():
    # Target: itl = 15.0, ratio = 4.0, md_density = 0.08
    run = SingleResult(
        prompt_sha256="ghi",
        status_code=200,
        rejected=False,
        error_type=None,
        latency_ms=750.0,
        ttft_ms=0.0,
        completion_tokens=50,
        tokens_per_sec=66.67,
        json_valid=False,
        exact_match=None,
        response_preview="#" * 16 + "a" * 184,
        timestamp_iso="2026-06-29"
    )
    analyzer = PassiveFingerprintAnalyzer([run])
    classification = analyzer.classify()
    assert classification["predicted_family"] == "Gemini_1_5_Pro"
    assert classification["confidence"] > 0.45
