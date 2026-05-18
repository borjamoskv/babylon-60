"""Tests for cortex/utils/sandbox.py — ASTSandbox coverage."""

from __future__ import annotations

import pytest

from cortex.utils.sandbox import ASTSandbox, ExecResult, SandboxVerdict


# ─── SandboxVerdict repr ──────────────────────────────────────────────


class TestSandboxVerdict:
    def test_safe_repr(self):
        v = SandboxVerdict(is_safe=True, node_count=5)
        assert "SAFE" in repr(v)
        assert "5 nodes" in repr(v)

    def test_unsafe_repr(self):
        v = SandboxVerdict(is_safe=False, violations=("bad1", "bad2"))
        assert "UNSAFE" in repr(v)
        assert "2 violations" in repr(v)


# ─── ASTSandbox.validate ─────────────────────────────────────────────


class TestASTSandboxValidate:
    def setup_method(self):
        self.sb = ASTSandbox()

    def test_safe_assignment(self):
        verdict = self.sb.validate("x = 2 + 3")
        assert verdict.is_safe is True
        assert verdict.node_count > 0

    def test_safe_loop(self):
        verdict = self.sb.validate("result = sum(range(10))")
        assert verdict.is_safe is True

    def test_safe_list_comprehension(self):
        verdict = self.sb.validate("[x*2 for x in range(5)]")
        assert verdict.is_safe is True

    def test_safe_conditional(self):
        verdict = self.sb.validate("y = 1 if True else 0")
        assert verdict.is_safe is True

    def test_import_blocked(self):
        verdict = self.sb.validate("import os")
        assert verdict.is_safe is False
        assert any("Import" in v for v in verdict.violations)

    def test_from_import_blocked(self):
        verdict = self.sb.validate("from pathlib import Path")
        assert verdict.is_safe is False
        assert any("Import" in v for v in verdict.violations)

    def test_eval_blocked(self):
        verdict = self.sb.validate("eval('1+1')")
        assert verdict.is_safe is False
        assert any("eval" in v.lower() for v in verdict.violations)

    def test_exec_blocked(self):
        verdict = self.sb.validate("exec('x=1')")
        assert verdict.is_safe is False

    def test_open_blocked(self):
        verdict = self.sb.validate("open('/etc/passwd')")
        assert verdict.is_safe is False

    def test_dunder_class_blocked(self):
        verdict = self.sb.validate("x = ().__class__")
        assert verdict.is_safe is False
        assert any("__class__" in v for v in verdict.violations)

    def test_dunder_import_call_blocked(self):
        verdict = self.sb.validate("__import__('os')")
        assert verdict.is_safe is False

    def test_syntax_error(self):
        verdict = self.sb.validate("def foo(: pass")
        assert verdict.is_safe is False
        assert any("SyntaxError" in v for v in verdict.violations)

    def test_class_definition_blocked(self):
        # ast.ClassDef not in whitelist
        verdict = self.sb.validate("class Foo: pass")
        assert verdict.is_safe is False

    def test_too_many_nodes(self):
        sb = ASTSandbox(max_nodes=3)
        # A long expression will exceed node count
        code = "x = " + " + ".join(["1"] * 100)
        verdict = sb.validate(code)
        assert verdict.is_safe is False
        assert any("node count" in v for v in verdict.violations)

    def test_depth_exceeded(self):
        sb = ASTSandbox(max_depth=2)
        # Deeply nested expression
        code = "x = (((((1+2)+3)+4)+5)+6)"
        verdict = sb.validate(code)
        # With max_depth=2, the deep nesting should violate
        assert verdict.is_safe is False

    def test_safe_function_def(self):
        verdict = self.sb.validate("def add(a, b): return a + b")
        assert verdict.is_safe is True

    def test_safe_lambda(self):
        verdict = self.sb.validate("f = lambda x: x * 2")
        assert verdict.is_safe is True

    def test_globals_blocked(self):
        verdict = self.sb.validate("globals()")
        assert verdict.is_safe is False


# ─── ASTSandbox.safe_exec ─────────────────────────────────────────────


class TestASTSandboxSafeExec:
    def setup_method(self):
        self.sb = ASTSandbox()

    def test_exec_safe_code(self):
        result = self.sb.safe_exec("x = 2 + 3\nresult = x * 10")
        assert result.success is True
        assert result.output["result"] == 50

    def test_exec_captures_user_vars(self):
        result = self.sb.safe_exec("a = 1\nb = 2\nc = a + b")
        assert result.output["c"] == 3

    def test_exec_unsafe_code_fails(self):
        result = self.sb.safe_exec("import os")
        assert result.success is False
        assert "Validation failed" in (result.error or "")

    def test_exec_runtime_error(self):
        # Division by zero — safe AST but runtime error
        result = self.sb.safe_exec("x = 1 / 0")
        assert result.success is False
        assert "ZeroDivisionError" in (result.error or "")

    def test_exec_captures_stdout(self):
        result = self.sb.safe_exec("print('hello')")
        assert result.success is True
        assert "hello" in result.stdout

    def test_exec_duration_recorded(self):
        result = self.sb.safe_exec("x = sum(range(100))")
        assert result.duration_ms >= 0

    def test_exec_hides_private_vars(self):
        result = self.sb.safe_exec("_private = 99\npublic = 1")
        assert "_private" not in result.output
        assert result.output["public"] == 1

    def test_exec_available_builtins(self):
        result = self.sb.safe_exec("result = len([1, 2, 3])")
        assert result.output["result"] == 3

    def test_exec_list_comprehension(self):
        result = self.sb.safe_exec("squares = [x**2 for x in range(5)]")
        assert result.output["squares"] == [0, 1, 4, 9, 16]

    def test_exec_result_dataclass_defaults(self):
        r = ExecResult(success=True)
        assert r.output == {}
        assert r.stdout == ""
        assert r.error is None
        assert r.duration_ms == 0.0


# ─── ASTSandbox._max_ast_depth ────────────────────────────────────────


class TestMaxASTDepth:
    def test_simple_depth(self):
        import ast

        code = "x = 1"
        tree = ast.parse(code)
        depth = ASTSandbox._max_ast_depth(tree)
        assert depth > 0

    def test_nested_deeper_than_flat(self):
        import ast

        flat = ast.parse("x = 1")
        nested = ast.parse("x = (((1+2)+3)+4)")
        assert ASTSandbox._max_ast_depth(nested) > ASTSandbox._max_ast_depth(flat)
