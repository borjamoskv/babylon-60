"""Tests for cortex/verification/ — extractor, frontend_oracle, counterexample."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from cortex.verification.extractor import SMTModelExtractor, extract_constraints
from cortex.verification.frontend_oracle import FrontendOracle
from cortex.verification.counterexample import learn_from_failure


# ─── SMTModelExtractor ────────────────────────────────────────────────


class TestSMTModelExtractor:
    def test_no_violations_for_clean_code(self):
        code = "x = 1\ny = x + 2"
        extractor = SMTModelExtractor(code)
        findings = extractor.analyze()
        assert findings == []

    def test_detects_delete_method_call(self):
        code = "obj.delete()"
        extractor = SMTModelExtractor(code)
        findings = extractor.analyze()
        assert any(f["invariant_id"] == "I2" for f in findings)
        assert any("delete" in f["message"] for f in findings)

    def test_detects_remove_method_call(self):
        code = "obj.remove(item)"
        extractor = SMTModelExtractor(code)
        findings = extractor.analyze()
        assert any(f["invariant_id"] == "I2" for f in findings)

    def test_detects_drop_table_method_call(self):
        code = "db.drop_table('users')"
        extractor = SMTModelExtractor(code)
        findings = extractor.analyze()
        assert any(f["invariant_id"] == "I2" for f in findings)

    def test_detects_eval_call(self):
        code = "eval('1+1')"
        extractor = SMTModelExtractor(code)
        findings = extractor.analyze()
        assert any(f["invariant_id"] == "I7" for f in findings)

    def test_for_loop_visited(self):
        code = "for x in items:\n    pass"
        extractor = SMTModelExtractor(code)
        findings = extractor.analyze()
        # No violation expected, but loop was visited without error
        assert isinstance(findings, list)

    def test_multiple_violations(self):
        code = "obj.delete()\neval('x')"
        extractor = SMTModelExtractor(code)
        findings = extractor.analyze()
        ids = {f["invariant_id"] for f in findings}
        assert "I2" in ids
        assert "I7" in ids


class TestExtractConstraints:
    def test_clean_code_no_findings(self):
        result = extract_constraints("x = 42")
        assert result == []

    def test_syntax_error_returns_syntax_finding(self):
        result = extract_constraints("def foo(: pass")
        assert len(result) == 1
        assert result[0]["invariant_id"] == "SYNTAX"
        assert "Code parsing failed" in result[0]["message"]

    def test_violation_detected(self):
        result = extract_constraints("eval('danger')")
        assert any(f["invariant_id"] == "I7" for f in result)


# ─── FrontendOracle ───────────────────────────────────────────────────


class TestFrontendOracle:
    def setup_method(self):
        self.oracle = FrontendOracle()

    def test_analyze_nonexistent_file_returns_empty(self):
        violations = self.oracle.analyze_file("/tmp/nonexistent_xyz.js")
        assert violations == []

    def test_analyze_simple_js_no_violations(self, tmp_path: Path):
        js = "function add(a, b) { return a + b; }"
        f = tmp_path / "test.js"
        f.write_text(js)
        violations = self.oracle.analyze_file(str(f))
        assert violations == []

    def test_analyze_complex_handler_flags_violation(self, tmp_path: Path):
        # Build a handler with complexity >= 5
        js = """
function handleUpdate(data) {
    if (data.a) {
        if (data.b) {
            if (data.c) {
                if (data.d) {
                    if (data.e) { return 1; }
                }
            }
        }
    }
}
"""
        f = tmp_path / "handler.js"
        f.write_text(js)
        violations = self.oracle.analyze_file(str(f))
        assert any(v["function"] == "handleUpdate" for v in violations)

    def test_analyze_html_file_extracts_script(self, tmp_path: Path):
        html = """<html><body>
<script>
function handleListener(x) {
    if (x.a) { if (x.b) { if (x.c) { if (x.d) { if (x.e) { return 1; } } } } }
}
</script>
</body></html>"""
        f = tmp_path / "page.html"
        f.write_text(html)
        violations = self.oracle.analyze_file(str(f))
        assert any(v["function"] == "handleListener" for v in violations)

    def test_calculate_complexity_counts_branches(self):
        body = "{ if (a) {} else if (b) {} for (;;) {} while (x) {} catch (e) {} switch(s) {} }"
        cc = self.oracle._calculate_complexity(body)
        assert cc >= 6  # if + else if + for + while + catch + switch

    def test_calculate_complexity_counts_logical_ops(self):
        body = "{ if (a && b || c) {} }"
        cc = self.oracle._calculate_complexity(body)
        assert cc >= 3  # if + && + ||

    def test_calculate_complexity_counts_ternaries(self):
        body = "{ x = a ? 1 : 0; y = b ? 2 : 3; }"
        cc = self.oracle._calculate_complexity(body)
        assert cc >= 2

    def test_extract_block_finds_matching_brace(self):
        text = "function foo() { x = 1; }"
        # start at the opening brace
        idx = text.index("{")
        block = self.oracle._extract_block(text, idx)
        assert block.startswith("{")
        assert block.endswith("}")

    def test_extract_block_fallback_on_unclosed(self):
        text = "{ unclosed"
        block = self.oracle._extract_block(text, 0)
        assert block == text  # fallback: return rest of text

    def test_arrow_function_handler_detected(self, tmp_path: Path):
        js = """
const handleUpdate = (data) => {
    if (data.a) { if (data.b) { if (data.c) { if (data.d) { if (data.e) { return 1; } } } } }
};
"""
        f = tmp_path / "arrow.js"
        f.write_text(js)
        violations = self.oracle.analyze_file(str(f))
        assert any(v["function"] == "handleUpdate" for v in violations)


# ─── learn_from_failure (counterexample) ─────────────────────────────


class TestLearnFromFailure:
    @pytest.mark.asyncio
    async def test_calls_memory_store(self):
        memory_manager = AsyncMock()
        memory_manager.store = AsyncMock()

        await learn_from_failure(
            memory_manager=memory_manager,
            tenant_id="test-tenant",
            project_id="proj-1",
            invariant_id="INV-001",
            violation_message="Ledger hash chain broken",
            counterexample={"state": "invalid"},
            file_path="cortex/ledger.py",
        )

        memory_manager.store.assert_called_once()
        call_kwargs = memory_manager.store.call_args.kwargs
        assert call_kwargs["tenant_id"] == "test-tenant"
        assert call_kwargs["fact_type"] == "error"
        assert "INV-001" in call_kwargs["content"]
        assert call_kwargs["metadata"]["is_toxic"] is True
        assert call_kwargs["metadata"]["is_formal_proof"] is True
        assert call_kwargs["metadata"]["confidence"] == "C5"

    @pytest.mark.asyncio
    async def test_content_contains_violation_message(self):
        memory_manager = AsyncMock()
        memory_manager.store = AsyncMock()

        await learn_from_failure(
            memory_manager=memory_manager,
            tenant_id="t1",
            project_id="p1",
            invariant_id="I2",
            violation_message="Isolation breached",
            counterexample={},
            file_path="engine/core.py",
        )

        content = memory_manager.store.call_args.kwargs["content"]
        assert "Isolation breached" in content
        assert "engine/core.py" in content
