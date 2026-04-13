"""Default Guard/Hook Adapters — Wraps existing AX-II implementations behind Protocols.

Each adapter wraps a concrete module (HealthGuard, ContradictionGuard, etc.)
behind the StoreGuard / PostStoreHook protocol so they can be registered in
the GuardPipeline without store_mixin.py importing them directly.
"""

from __future__ import annotations

import logging
from typing import Any

import aiosqlite

__all__ = [
    "HealthGuardAdapter",
    "ContradictionGuardAdapter",
    "VerifierGuardAdapter",
    "ExergyGuardAdapter",
    "ZKGuardAdapter",
    "LedgerCheckpointHook",
    "SignalEmitHook",
    "EpistemicBreakerHook",
]

logger = logging.getLogger("cortex.engine")


# ─── Pre-Store Guards ─────────────────────────────────────────────


class HealthGuardAdapter:
    """AX-II Hook 1 → StoreGuard protocol."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        from cortex.guards.health_guard import HealthGuard

        # Batch writes may already hold an open SQLite transaction on this
        # connection. Re-running the sidecar health collector through db_path
        # would contend with the current writer and can self-deadlock.
        if getattr(conn, "in_transaction", False):
            return

        guard = HealthGuard(db_path=self._db_path)
        await guard.check_write_safety()


class ContradictionGuardAdapter:
    """AX-II Hook 2 → StoreGuard protocol (decision/rule/error types only)."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        if fact_type not in ("decision", "rule", "error"):
            return
        from cortex.guards.contradiction_guard import detect_contradictions

        report = await detect_contradictions(
            new_content=content,
            new_project=project,
            db_path=self._db_path,
            tenant_id=tenant_id,
        )

        if not report.has_conflicts:
            return

        message = (
            f"[AX-II] Contradiction detected (severity={report.severity}):\n"
            f"{report.format()}"
        )
        if report.severity == "high":
            raise ValueError(
                "Write rejected due to contradiction with existing canonical fact.\n"
                f"{message}"
            )

        logger.warning(message)


class VerifierGuardAdapter:
    """AX-II Hook 3 → StoreGuard protocol (code-type formal verification)."""

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        if fact_type != "code":
            return
        from cortex.verification.verifier import SovereignVerifier

        result = SovereignVerifier().check(content, context={"project": project})
        if not result.is_valid:
            violation_names = [v.get("name", "unknown") for v in result.violations]
            raise ValueError(
                f"[AX-II] Formal verification failed: {violation_names}. "
                f"Counterexample: {result.counterexample}"
            )


class ExergyGuardAdapter:
    """AX-II Hook -> StoreGuard protocol (thermodynamic filter)."""

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        from cortex.guards.exergy_guard import ExergyGuard

        guard = ExergyGuard()
        guard.check_thermodynamic_yield(content, project, fact_type, source=meta.get("source"))


class ZKGuardAdapter:
    """AX-II Hook -> StoreGuard protocol (ZK-Swarm cryptographic check)."""

    def __init__(self, engine: Any | None = None) -> None:
        self._engine = engine

    async def check(
        self,
        content: str,
        project: str,
        fact_type: str,
        meta: dict[str, Any],
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
    ) -> None:
        from cortex.guards.zk_guard import ZKSwarmGuard

        proof_attestor = getattr(self._engine, "_attest_high_rigor_fact", None)
        if callable(proof_attestor) and (
            not meta.get("agent_public_key") or not meta.get("zk_proof_signature")
        ):
            enriched_meta = proof_attestor(
                content=content,
                fact_type=fact_type,
                source=meta.get("source"),
                meta=meta,
            )
            if enriched_meta is not None:
                meta.clear()
                meta.update(enriched_meta)

        guard = ZKSwarmGuard()
        await guard.verify_integrity(content, fact_type, meta)


# ─── Post-Store Hooks ─────────────────────────────────────────────


class LedgerCheckpointHook:
    """AX-II Hook 4 → PostStoreHook protocol."""

    critical = True
    requires_committed_write = False

    def __init__(self, engine: Any) -> None:
        self._engine = engine

    async def on_stored(
        self,
        fact_id: int,
        project: str,
        fact_type: str,
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
        db_path: str | None = None,
    ) -> None:
        ledger = getattr(self._engine, "_ledger", None)
        if ledger is not None and hasattr(ledger, "create_checkpoint_async"):
            if hasattr(ledger, "record_write"):
                ledger.record_write()
            try:
                await ledger.create_checkpoint_async(tenant_id=tenant_id)
            except TypeError:
                await ledger.create_checkpoint_async()


class SignalEmitHook:
    """Signal emission → PostStoreHook protocol."""

    critical = False
    requires_committed_write = True

    async def on_stored(
        self,
        fact_id: int,
        project: str,
        fact_type: str,
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
        db_path: str | None = None,
    ) -> None:
        from cortex.extensions.signals.fact_hook import emit_fact_stored

        if db_path:
            emit_fact_stored(
                db_path=db_path,
                fact_id=fact_id,
                project=project,
                fact_type=fact_type,
                source=source or "engine:store",
                tenant_id=tenant_id,
            )


class EpistemicBreakerHook:
    """Epistemic Circuit Breaker → PostStoreHook protocol."""

    critical = False
    requires_committed_write = False

    def __init__(self) -> None:
        from cortex.extensions.daemon.epistemic_breaker import EpistemicBreakerDaemon

        evaluator = getattr(EpistemicBreakerDaemon, "evaluate", None)
        if evaluator is None:
            raise RuntimeError("EpistemicBreakerDaemon.evaluate is unavailable")
        self._evaluator = evaluator

    async def on_stored(
        self,
        fact_id: int,
        project: str,
        fact_type: str,
        conn: aiosqlite.Connection,
        *,
        tenant_id: str = "default",
        source: str | None = None,
        db_path: str | None = None,
    ) -> None:
        await self._evaluator(  # type: ignore[misc]
            conn,
            tenant_id,
            project,
        )
