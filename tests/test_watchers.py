"""Tests for WatchdogHub."""

import pytest

from cortex.extensions.daemon.watchers import DEFAULT_PATTERNS, EXCLUDE_DIRS, WatchdogHub


class TestWatchdogHubInit:
    def test_default_patterns(self):
        hub = WatchdogHub()
        assert hub._patterns == DEFAULT_PATTERNS

    def test_custom_patterns(self):
        hub = WatchdogHub(patterns=["*.rs", "*.go"])
        assert "*.rs" in hub._patterns

    def test_path_expansion(self, tmp_path):
        hub = WatchdogHub(paths=[str(tmp_path)])
        assert hub._paths[0] == tmp_path.resolve()

    def test_no_paths_idle(self):
        hub = WatchdogHub(paths=[])
        assert not hub.is_running


class TestWatchdogHubLifecycle:
    @pytest.mark.asyncio
    async def test_start_stop(self, tmp_path):
        hub = WatchdogHub(paths=[str(tmp_path)])
        await hub.start()
        assert hub.is_running
        await hub.stop()
        assert not hub.is_running

    @pytest.mark.asyncio
    async def test_start_no_paths(self):
        hub = WatchdogHub(paths=[])
        await hub.start()
        # Should not crash, just log "no paths"
        assert not hub.is_running

    @pytest.mark.asyncio
    async def test_add_path_hot(self, tmp_path):
        sub = tmp_path / "sub"
        sub.mkdir()
        hub = WatchdogHub(paths=[str(tmp_path)])
        await hub.start()
        hub.add_path(str(sub))
        assert sub.resolve() in hub._paths
        await hub.stop()


class TestExcludeDirs:
    def test_common_excludes_present(self):
        assert ".git" in EXCLUDE_DIRS
        assert "__pycache__" in EXCLUDE_DIRS
        assert "node_modules" in EXCLUDE_DIRS
        assert ".venv" in EXCLUDE_DIRS
