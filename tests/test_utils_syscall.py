"""Tests for cortex/utils/syscall.py — SovereignSys coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from cortex.utils.syscall import SovereignSys


@pytest.fixture
def sys_ctrl(tmp_path: Path) -> SovereignSys:
    return SovereignSys(tmp_path)


class TestSovereignSysInit:
    def test_root_resolved(self, tmp_path: Path):
        sc = SovereignSys(str(tmp_path))
        assert sc.root == tmp_path.resolve()

    def test_accepts_path_object(self, tmp_path: Path):
        sc = SovereignSys(tmp_path)
        assert sc.root == tmp_path


class TestSovereignSysIsSafe:
    def test_file_within_root_is_safe(self, sys_ctrl: SovereignSys, tmp_path: Path):
        (tmp_path / "file.txt").write_text("x")
        assert sys_ctrl._is_safe("file.txt") is True

    def test_path_outside_root_not_safe(self, sys_ctrl: SovereignSys):
        assert sys_ctrl._is_safe("../../etc/passwd") is False

    def test_root_itself_is_safe(self, sys_ctrl: SovereignSys):
        assert sys_ctrl._is_safe(".") is True


class TestSovereignSysBash:
    def test_echo_command(self, sys_ctrl: SovereignSys):
        result = sys_ctrl.bash(["echo", "sovereign"])
        assert "sovereign" in result

    def test_nonexistent_command_returns_error(self, sys_ctrl: SovereignSys):
        result = sys_ctrl.bash(["nonexistent_cmd_xyz_abc"])
        assert "[ERROR]" in result

    def test_timeout_returns_error(self, sys_ctrl: SovereignSys):
        result = sys_ctrl.bash(["sleep", "10"], timeout=0)
        assert "[ERROR]" in result


class TestSovereignSysRead:
    def test_read_existing_file(self, sys_ctrl: SovereignSys, tmp_path: Path):
        (tmp_path / "test.txt").write_text("hello cortex")
        result = sys_ctrl.read("test.txt")
        assert result == "hello cortex"

    def test_read_outside_sandbox_denied(self, sys_ctrl: SovereignSys):
        result = sys_ctrl.read("../../etc/passwd")
        assert "[ERROR] Access denied" in result

    def test_read_nonexistent_file_returns_error(self, sys_ctrl: SovereignSys):
        result = sys_ctrl.read("nonexistent.txt")
        assert "[ERROR]" in result


class TestSovereignSysWrite:
    def test_write_new_file(self, sys_ctrl: SovereignSys, tmp_path: Path):
        result = sys_ctrl.write("output.txt", "sovereign content")
        assert "[SUCCESS]" in result
        assert (tmp_path / "output.txt").read_text() == "sovereign content"

    def test_write_creates_parent_dirs(self, sys_ctrl: SovereignSys, tmp_path: Path):
        result = sys_ctrl.write("sub/dir/file.txt", "deep")
        assert "[SUCCESS]" in result
        assert (tmp_path / "sub" / "dir" / "file.txt").exists()

    def test_write_outside_sandbox_denied(self, sys_ctrl: SovereignSys):
        result = sys_ctrl.write("../../etc/passwd", "evil")
        assert "[ERROR] Access denied" in result


class TestSovereignSysListDir:
    def test_list_empty_dir(self, sys_ctrl: SovereignSys):
        result = sys_ctrl.list_dir(".")
        assert result == "(empty)"

    def test_list_with_files(self, sys_ctrl: SovereignSys, tmp_path: Path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        result = sys_ctrl.list_dir(".")
        assert "a.txt" in result
        assert "b.txt" in result

    def test_list_marks_directories(self, sys_ctrl: SovereignSys, tmp_path: Path):
        (tmp_path / "subdir").mkdir()
        result = sys_ctrl.list_dir(".")
        assert "subdir/" in result

    def test_list_outside_sandbox_denied(self, sys_ctrl: SovereignSys):
        result = sys_ctrl.list_dir("../../etc")
        assert "[ERROR] Access denied" in result

    def test_list_nonexistent_returns_error(self, sys_ctrl: SovereignSys):
        result = sys_ctrl.list_dir("nonexistent_dir")
        assert "[ERROR]" in result
