from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from cortex.auth.deps import require_auth
from cortex.auth.models import AuthResult
from cortex.routes import swarm as swarm_router

TEST_AUTH = AuthResult(
    authenticated=True,
    tenant_id="default",
    permissions=["read", "write", "admin"],
    key_name="test_agent",
)


@dataclass
class _FakeWorktreeState:
    id: str
    branch_name: str
    path: Path
    status: str
    created_at: str


class _FakeSwarmManager:
    """Minimal in-memory swarm manager used to isolate API route tests."""

    def __init__(self) -> None:
        self.worktrees: dict[str, _FakeWorktreeState] = {}
        self._next_id = 0

    async def get_status(self) -> dict[str, object]:
        return {
            "active_worktrees": len(
                [worktree for worktree in self.worktrees.values() if worktree.status == "active"]
            ),
            "total_worktrees": len(self.worktrees),
            "agent_pids": [12345],
            "timestamp": "2026-01-01T00:00:00Z",
        }

    async def create_worktree(
        self, branch_name: str, base_path: str | None = None
    ) -> _FakeWorktreeState:
        self._next_id += 1
        worktree_id = f"wt-{self._next_id}"
        root = Path(base_path or "/tmp")
        state = _FakeWorktreeState(
            id=worktree_id,
            branch_name=branch_name,
            path=root / worktree_id,
            status="active",
            created_at="2026-01-01T00:00:00Z",
        )
        self.worktrees[worktree_id] = state
        return state

    async def get_worktree(self, worktree_id: str) -> _FakeWorktreeState | None:
        return self.worktrees.get(worktree_id)

    async def delete_worktree(self, worktree_id: str) -> bool:
        state = self.worktrees.get(worktree_id)
        if state is None:
            return False
        state.status = "tearing_down"
        return True


async def override_auth() -> AuthResult:
    return TEST_AUTH


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = FastAPI()
    app.include_router(swarm_router.router)
    app.state.swarm_manager = _FakeSwarmManager()
    app.dependency_overrides[require_auth] = override_auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_swarm_worktree_lifecycle_api(client: AsyncClient) -> None:
    resp = await client.get("/v1/swarm/status")
    assert resp.status_code == 200
    assert "active_worktrees" in resp.json()

    resp = await client.post("/v1/swarm/worktrees", json={"branch_name": "test_branch"})
    assert resp.status_code == 200
    data = resp.json()
    wt_id = data["id"]
    assert data["status"] == "active"

    resp = await client.get(f"/v1/swarm/worktrees/{wt_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == wt_id

    resp = await client.delete(f"/v1/swarm/worktrees/{wt_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "tearing_down"
