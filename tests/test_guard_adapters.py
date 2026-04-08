from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.engine.guard_adapters import ContradictionGuardAdapter, ZKGuardAdapter


@pytest.mark.asyncio
async def test_zk_guard_adapter_skips_plain_decision_without_zk_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verify_integrity = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "cortex.guards.zk_guard.ZKSwarmGuard.verify_integrity",
        verify_integrity,
    )

    adapter = ZKGuardAdapter()
    await adapter.check(
        content="manual decision",
        project="alpha",
        fact_type="decision",
        meta={"source": "api"},
        conn=MagicMock(),
    )

    verify_integrity.assert_not_awaited()


@pytest.mark.asyncio
async def test_zk_guard_adapter_enforces_when_proof_is_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verify_integrity = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "cortex.guards.zk_guard.ZKSwarmGuard.verify_integrity",
        verify_integrity,
    )

    adapter = ZKGuardAdapter()
    await adapter.check(
        content="agent decision",
        project="alpha",
        fact_type="decision",
        meta={"requires_zk_proof": True, "source": "agent:test"},
        conn=MagicMock(),
    )

    verify_integrity.assert_awaited_once()


@pytest.mark.asyncio
async def test_zk_guard_adapter_enforces_when_signature_fields_are_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verify_integrity = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "cortex.guards.zk_guard.ZKSwarmGuard.verify_integrity",
        verify_integrity,
    )

    adapter = ZKGuardAdapter()
    await adapter.check(
        content="signed decision",
        project="alpha",
        fact_type="decision",
        meta={
            "source": "api",
            "agent_public_key": "pubkey",
            "zk_proof_signature": "sig",
        },
        conn=MagicMock(),
    )

    verify_integrity.assert_awaited_once()


@pytest.mark.asyncio
async def test_zk_guard_adapter_skips_github_bridge_decisions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verify_integrity = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "cortex.guards.zk_guard.ZKSwarmGuard.verify_integrity",
        verify_integrity,
    )

    adapter = ZKGuardAdapter()
    await adapter.check(
        content="github crystallization",
        project="alpha",
        fact_type="decision",
        meta={"source_bridge_provider": "github", "requires_zk_proof": True},
        conn=MagicMock(),
    )

    verify_integrity.assert_not_awaited()


@pytest.mark.asyncio
async def test_contradiction_guard_adapter_forwards_conn_and_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    detect_contradictions = AsyncMock(
        return_value=SimpleNamespace(has_conflicts=False, severity="clean")
    )
    monkeypatch.setattr(
        "cortex.guards.contradiction_guard.detect_contradictions",
        detect_contradictions,
    )

    adapter = ContradictionGuardAdapter(db_path="/tmp/test.db")
    conn = MagicMock()

    await adapter.check(
        content="decision content",
        project="alpha",
        fact_type="decision",
        meta={},
        conn=conn,
        tenant_id="tenant-alpha",
    )

    detect_contradictions.assert_awaited_once_with(
        new_content="decision content",
        new_project="alpha",
        db_path="/tmp/test.db",
        conn=conn,
        tenant_id="tenant-alpha",
    )
