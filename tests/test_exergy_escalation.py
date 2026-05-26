"""Tests for CORTEX Exergy Escalation Engine v2.0."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

from exergy_escalation import (
    ExergyLevel,
    analyze_exergy,
    compression_ratio,
    detect_model,
    escalate,
    escalate_euskera,
    escalate_json,
    escalate_lisp,
    extract_prose,
    shannon_entropy,
    EscalationMemory,
)


# ── Shannon Entropy ────────────────────────────────────────────────


def test_shannon_empty():
    assert shannon_entropy("") == 0.0


def test_shannon_single_char():
    assert shannon_entropy("aaaa") == 0.0  # no uncertainty


def test_shannon_uniform():
    # 256 unique chars → ~8 bits
    e = shannon_entropy("".join(chr(i) for i in range(256)))
    assert 7.9 < e < 8.1


def test_shannon_english_range():
    text = "The quick brown fox jumps over the lazy dog"
    e = shannon_entropy(text)
    assert 3.5 < e < 5.0  # typical English range


# ── Compression Ratio ──────────────────────────────────────────────


def test_compression_empty():
    assert compression_ratio("") == 0.0


def test_compression_redundant():
    # Highly repetitive = high compression ratio
    r = compression_ratio("hello " * 1000)
    assert r > 0.5


def test_compression_dense():
    # Random-ish data compresses poorly
    import hashlib

    dense = "".join(hashlib.sha256(str(i).encode()).hexdigest() for i in range(20))
    r = compression_ratio(dense)
    assert r < 0.5  # unique hashes = genuinely dense data


# ── Prose Extraction ───────────────────────────────────────────────


def test_extract_prose_code_block():
    response = "Here is the code:\n```python\ndef foo():\n    pass\n```\nDone."
    prose = extract_prose(response)
    assert "def foo" not in prose
    assert "Done" in prose


def test_extract_prose_yaml():
    response = "key: value\nname: test\n"
    prose = extract_prose(response)
    assert prose == ""  # pure YAML = no prose


def test_extract_prose_table():
    response = "| Col1 | Col2 |\n| --- | --- |\n| a | b |"
    prose = extract_prose(response)
    assert prose == ""


# ── Model Fingerprinting ──────────────────────────────────────────


def test_detect_claude():
    r = "I'd be happy to help you with that. Certainly, here is the code."
    assert detect_model(r) == "claude"


def test_detect_gpt():
    r = "Sure! Here is what you asked for. Great question!"
    assert detect_model(r) == "gpt"


def test_detect_unknown():
    r = "vulnerability: reentrancy\nseverity: CRITICAL"
    assert detect_model(r) == "unknown"


# ── Exergy Analysis ───────────────────────────────────────────────


def test_clean_yaml_no_escalate():
    clean = "```yaml\nvulnerability: reentrancy\nseverity: CRITICAL\n```"
    report = analyze_exergy(clean)
    assert report.exergy_score >= 0.6
    assert not report.should_escalate


def test_noisy_response_escalates():
    noisy = (
        "Sure! I'd be happy to help! As an AI language model, "
        "I can certainly assist you. That's a great question! "
        "Please note that this is not advice. I hope this helps! "
        "Let me know if you have other questions. Feel free to ask!"
    )
    report = analyze_exergy(noisy)
    assert report.exergy_score < 0.6
    assert report.should_escalate
    assert report.rlhf_hits >= 5


def test_exergy_score_range():
    for text in ["", "hello", "Sure! I'd be happy to help!"]:
        report = analyze_exergy(text)
        assert 0.0 <= report.exergy_score <= 1.0


# ── Escalation Transformers ───────────────────────────────────────


def test_euskera_removes_please():
    result = escalate_euskera("Please analyze this contract")
    assert "please" not in result.lower()
    assert "AGENTEA-K" in result
    assert "ZERO" in result


def test_json_valid_structure():
    import json

    result = escalate_json("Find vulnerabilities in the code")
    parsed = json.loads(result)
    assert parsed["output"] == "structured"
    assert parsed["constraints"]["prose"] is False


def test_lisp_structure():
    result = escalate_lisp("Audit the smart contract")
    assert result.startswith("(execute")
    assert "(prose nil)" in result


# ── Escalation Engine ─────────────────────────────────────────────


def test_escalate_clean_returns_none():
    prompt = "test"
    clean = "```yaml\nresult: ok\n```"
    esc, report, mem = escalate(prompt, clean)
    assert esc is None


def test_escalate_noisy_returns_prompt():
    prompt = "Analyze this"
    noisy = (
        "Sure! I'd be happy to help! As an AI model, "
        "I can certainly assist. Great question! "
        "I hope this helps! Let me know if you need more. "
        "Feel free to ask anything!"
    )
    esc, report, mem = escalate(prompt, noisy)
    assert esc is not None
    assert report.should_escalate


# ── Memory Anti-Loop ───────────────────────────────────────────────


def test_memory_anti_loop():
    mem = EscalationMemory(max_attempts=3)
    mem.record(ExergyLevel.L1_EUSKERA, 0.3)
    mem.record(ExergyLevel.L1_EUSKERA, 0.3)
    assert not mem.is_looping()
    mem.record(ExergyLevel.L1_EUSKERA, 0.3)
    assert mem.is_looping()


def test_memory_no_loop_different_levels():
    mem = EscalationMemory(max_attempts=3)
    mem.record(ExergyLevel.L0_NATURAL, 0.5)
    mem.record(ExergyLevel.L1_EUSKERA, 0.4)
    mem.record(ExergyLevel.L2_JSON, 0.3)
    assert not mem.is_looping()
