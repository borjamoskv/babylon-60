"""Tests for cortex.sync.github_bridge — GitHub → CORTEX Bridge.

All GitHub API calls are mocked via httpx.MockTransport.
Uses CortexEngine with a temp database for realistic end-to-end testing.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from click.testing import CliRunner

import cortex.cli.github_cmds as github_cli
from cortex.extensions.sync.github_bridge import GitHubCortexBridge, _github_key

pytestmark = pytest.mark.slow


# ─── Fixtures ────────────────────────────────────────────────────────


def _make_issue(
    number: int,
    title: str = "Test issue",
    state: str = "open",
    is_pr: bool = False,
    labels: list[str] | None = None,
    body: str = "Issue body content for testing purposes.",
) -> dict:
    """Factory for GitHub API issue JSON."""
    item: dict = {
        "number": number,
        "title": title,
        "state": state,
        "body": body,
        "html_url": f"https://github.com/borjamoskv/testrepo/issues/{number}",
        "labels": [{"name": lb} for lb in (labels or [])],
        "updated_at": "2026-03-13T12:00:00Z",
        "created_at": "2026-03-13T10:00:00Z",
    }
    if state == "closed":
        item["closed_at"] = "2026-03-13T14:00:00Z"
    if is_pr:
        item["pull_request"] = {
            "url": f"https://api.github.com/repos/borjamoskv/testrepo/pulls/{number}"
        }
    return item


def _mock_transport(routes: dict[str, list]) -> httpx.MockTransport:
    """Create a MockTransport routing URL patterns to JSON responses."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        for pattern, data in routes.items():
            if pattern in path:
                return httpx.Response(200, json=data)
        return httpx.Response(404, json={"message": "Not Found"})

    return httpx.MockTransport(handler)


@pytest.fixture
async def engine(tmp_path: Path):
    """Create a CortexEngine with a temp database."""
    from cortex.engine import CortexEngine

    db = str(tmp_path / "test_gh_bridge.db")
    e = CortexEngine(db_path=db, auto_embed=False)
    await e.init_db()
    yield e
    await e.close()


# ─── Tests ───────────────────────────────────────────────────────────


class TestGitHubKey:
    def test_deterministic(self):
        k1 = _github_key("borjamoskv/Cortex-Persist", 42)
        k2 = _github_key("borjamoskv/Cortex-Persist", 42)
        assert k1 == k2

    def test_different_for_different_inputs(self):
        k1 = _github_key("borjamoskv/Cortex-Persist", 1)
        k2 = _github_key("borjamoskv/Cortex-Persist", 2)
        assert k1 != k2


class TestSyncCreatesBridgeFacts:
    async def test_sync_creates_bridge_facts(self, engine):
        """Mock 2 open issues → verify 2 bridge facts stored."""
        issues = [
            _make_issue(1, title="Fix auth bug"),
            _make_issue(2, title="Add logging", is_pr=True),
        ]
        repos = [{"full_name": "borjamoskv/testrepo", "fork": False}]

        transport = _mock_transport(
            {
                "/users/borjamoskv/repos": repos,
                "/repos/borjamoskv/testrepo/issues": issues,
            }
        )

        bridge = GitHubCortexBridge(engine, token="fake-token", owner="borjamoskv")
        bridge._client = httpx.AsyncClient(transport=transport)

        result = await bridge.sync_all()

        assert result.issues_synced == 1
        assert result.prs_synced == 1
        assert result.repos_scanned == 1
        assert result.crystallized == 0

        await bridge.close()


class TestSyncSkipsDuplicates:
    async def test_sync_skips_duplicates(self, engine):
        """Run sync twice → second run returns skipped > 0."""
        issues = [_make_issue(10, title="Unique issue for dedup test")]
        repos = [{"full_name": "borjamoskv/testrepo", "fork": False}]

        transport = _mock_transport(
            {
                "/users/borjamoskv/repos": repos,
                "/repos/borjamoskv/testrepo/issues": issues,
            }
        )

        bridge = GitHubCortexBridge(engine, token="fake-token", owner="borjamoskv")
        bridge._client = httpx.AsyncClient(transport=transport)

        # First sync — should create
        r1 = await bridge.sync_all()
        assert r1.issues_synced == 1

        # Second sync — should skip
        bridge._client = httpx.AsyncClient(transport=transport)
        r2 = await bridge.sync_all()
        assert r2.skipped >= 1
        assert r2.issues_synced == 0

        await bridge.close()


class TestClosedIssueCrystallizes:
    async def test_closed_issue_crystallizes(self, engine):
        """Store an open issue, then sync with it closed → crystallize."""
        # Step 1: Sync with open issue
        open_issues = [_make_issue(20, title="Will close soon")]
        repos = [{"full_name": "borjamoskv/testrepo", "fork": False}]

        transport = _mock_transport(
            {
                "/users/borjamoskv/repos": repos,
                "/repos/borjamoskv/testrepo/issues": open_issues,
            }
        )

        bridge = GitHubCortexBridge(engine, token="fake-token", owner="borjamoskv")
        bridge._client = httpx.AsyncClient(transport=transport)
        r1 = await bridge.sync_all()
        assert r1.issues_synced == 1

        # Step 2: Sync again with the issue now closed
        closed_issues = [_make_issue(20, title="Will close soon", state="closed")]
        transport2 = _mock_transport(
            {
                "/users/borjamoskv/repos": repos,
                "/repos/borjamoskv/testrepo/issues": closed_issues,
            }
        )
        bridge._client = httpx.AsyncClient(transport=transport2)
        r2 = await bridge.sync_all()
        assert r2.crystallized == 1
        assert r2.issues_synced == 0

        await bridge.close()


class TestPRDetected:
    async def test_pr_detected_as_pr(self, engine):
        """Mock item with pull_request key → verify meta.github_type == 'pr'."""
        issues = [_make_issue(30, title="Feature PR", is_pr=True)]
        repos = [{"full_name": "borjamoskv/testrepo", "fork": False}]

        transport = _mock_transport(
            {
                "/users/borjamoskv/repos": repos,
                "/repos/borjamoskv/testrepo/issues": issues,
            }
        )

        bridge = GitHubCortexBridge(engine, token="fake-token", owner="borjamoskv")
        bridge._client = httpx.AsyncClient(transport=transport)
        result = await bridge.sync_all()

        assert result.prs_synced == 1
        assert result.issues_synced == 0

        await bridge.close()


class TestAuthFailureGraceful:
    async def test_auth_failure_graceful(self, engine):
        """Mock 401 → verify error in SyncResult.errors, no crash."""

        def error_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"message": "Bad credentials"})

        transport = httpx.MockTransport(error_handler)
        bridge = GitHubCortexBridge(engine, token="bad-token", owner="borjamoskv")
        bridge._client = httpx.AsyncClient(transport=transport)

        result = await bridge.sync_all()

        assert len(result.errors) >= 1
        assert "401" in result.errors[0]

        await bridge.close()


class TestTenantAwareDedup:
    async def test_load_existing_keys_threads_tenant(self, engine, monkeypatch):
        calls: dict[str, object] = {}

        class _FakeCursor:
            async def fetchall(self):
                return [(123, b"encrypted-meta")]

        class _FakeConn:
            async def execute(self, sql, params):
                calls["sql"] = sql
                calls["params"] = params
                return _FakeCursor()

        class _FakeSession:
            async def __aenter__(self):
                return _FakeConn()

            async def __aexit__(self, exc_type, exc, tb):
                return None

        class _FakeEncrypter:
            def __init__(self):
                self.decrypt_calls: list[tuple[bytes, str]] = []

            def decrypt_json(self, payload, tenant_id="default"):
                self.decrypt_calls.append((payload, tenant_id))
                return {"github_key": "abc123"}

        fake_encrypter = _FakeEncrypter()

        bridge = GitHubCortexBridge(
            engine,
            token="fake-token",
            owner="borjamoskv",
            tenant_id="tenant-a",
        )
        monkeypatch.setattr(engine, "session", lambda: _FakeSession())
        monkeypatch.setattr("cortex.crypto.get_default_encrypter", lambda: fake_encrypter)

        index = await bridge._load_existing_keys()

        assert index == {"abc123": 123}
        assert calls["params"] == ("bridge:github", "tenant-a")
        assert fake_encrypter.decrypt_calls == [(b"encrypted-meta", "tenant-a")]
        await bridge.close()


class TestTenantAwareCrystallization:
    async def test_crystallize_decision_threads_tenant_into_deprecate_and_store(self):
        class _FakeEngine:
            def __init__(self) -> None:
                self.deprecate_calls: list[dict[str, object]] = []
                self.store_calls: list[dict[str, object]] = []

            async def deprecate(self, fact_id: int, **kwargs):
                self.deprecate_calls.append({"fact_id": fact_id, **kwargs})
                return True

            async def store(self, **kwargs):
                self.store_calls.append(kwargs)
                return 456

        engine = _FakeEngine()
        bridge = GitHubCortexBridge(
            engine,
            token="fake-token",
            owner="borjamoskv",
            tenant_id="tenant-a",
        )

        item = _make_issue(21, title="Closed item", state="closed")
        fact_id = await bridge._crystallize_decision(item, "borjamoskv/testrepo", 123)

        assert fact_id == 456
        assert engine.deprecate_calls == [
            {
                "fact_id": 123,
                "reason": "crystallized:closed:borjamoskv/testrepo#21",
                "tenant_id": "tenant-a",
            }
        ]
        assert engine.store_calls[0]["tenant_id"] == "tenant-a"
        assert engine.store_calls[0]["fact_type"] == "decision"
        await bridge.close()


class TestGithubStatusTenantScope:
    def test_status_filters_by_tenant(self, monkeypatch):
        calls: list[tuple[str, tuple[str, ...]]] = []

        class _FakeCursor:
            def __init__(self, value):
                self._value = value

            async def fetchone(self):
                return (self._value,)

        class _FakeConn:
            async def execute(self, sql, params):
                calls.append((sql, params))
                if "COUNT(*)" in sql and "fact_type = 'bridge'" in sql:
                    return _FakeCursor(7)
                if "COUNT(*)" in sql and "fact_type = 'decision'" in sql:
                    return _FakeCursor(3)
                return _FakeCursor("2026-04-04T12:00:00Z")

        class _FakeEngine:
            async def init_db(self):
                return None

            def session(self):
                class _Session:
                    async def __aenter__(self_inner):
                        return _FakeConn()

                    async def __aexit__(self_inner, exc_type, exc, tb):
                        return None

                return _Session()

            async def close(self):
                return None

        monkeypatch.setattr(github_cli, "get_engine", lambda db: _FakeEngine())

        result = CliRunner().invoke(
            github_cli.github_cmds,
            ["status", "--tenant-id", "tenant-a", "--db", "/tmp/db.sqlite"],
        )

        assert result.exit_code == 0, result.output
        assert "tenant-a" in result.output
        assert any(params == ("tenant-a",) for _, params in calls)
        assert len(calls) == 3
