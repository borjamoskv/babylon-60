"""Tests for cortex-core/mirror_audit.py — The Epistemic Auditor."""

from __future__ import annotations

import os
import sys
import tempfile
import pytest

# Make cortex-core importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

import mirror_audit  # noqa: E402


def test_clean_file_no_findings():
    code = """def simple_function(a, b):
    return a + b
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        auditor = mirror_audit.MirrorAuditor(tmp_path)
        assert auditor.audit() is True
        report = auditor.report()
        assert report["exergy_score"] == 100.0
        assert len(report["findings"]) == 0
        assert report["status"] == "OPTIMAL"
    finally:
        os.remove(tmp_path)


def test_hot_loop_detection():
    code = """def infinite_loop():
    while True:
        x = 1
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        auditor = mirror_audit.MirrorAuditor(tmp_path)
        assert auditor.audit() is True
        report = auditor.report()
        assert report["exergy_score"] == 80.0
        assert len(report["findings"]) == 1
        assert report["findings"][0]["type"] == "HOT_LOOP"
        assert report["findings"][0]["severity"] == "CRITICAL"
        assert report["status"] == "OPTIMAL"  # 80 >= 80 is OPTIMAL
    finally:
        os.remove(tmp_path)


def test_synchronous_blockage_detection():
    code = """def blocked_function():
    print("blocking operation")
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        auditor = mirror_audit.MirrorAuditor(tmp_path)
        assert auditor.audit() is True
        report = auditor.report()
        assert report["exergy_score"] == 95.0
        assert len(report["findings"]) == 1
        assert report["findings"][0]["type"] == "SYNCHRONOUS_BLOCK"
        assert report["findings"][0]["severity"] == "WARNING"
    finally:
        os.remove(tmp_path)


def test_high_complexity_detection():
    # Build a function with high complexity (>25)
    # We need 25 decision points. We can write a bunch of if statements.
    ifs = "\n    ".join(f"if x == {i}: pass" for i in range(30))
    code = f"""def complex_function(x):
    {ifs}
"""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        auditor = mirror_audit.MirrorAuditor(tmp_path)
        assert auditor.audit() is True
        report = auditor.report()
        assert report["exergy_score"] == 90.0  # 100 - 10
        assert any(f["type"] == "HIGH_COMPLEXITY" for f in report["findings"])
    finally:
        os.remove(tmp_path)
